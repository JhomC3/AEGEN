import json
import logging
import time
from typing import Any

from src.core.profile_manager import user_profile_manager
from src.memory.evolution_applier import apply_evolution
from src.memory.evolution_detector import EvolutionDetector
from src.memory.session_logger import log_session_to_memory

logger = logging.getLogger(__name__)


class ConsolidationManager:
    """Gestiona la consolidación de memoria."""

    def __init__(self) -> None:
        try:
            from src.core.llm_registry import get_llm

            detector_llm = get_llm("rag_summarization")
        except Exception:
            from src.core.llm_registry import get_llm

            detector_llm = get_llm("chat_response")
        self.evolution_detector = EvolutionDetector(detector_llm)

    async def should_consolidate(self, chat_id: str, message_count: int) -> bool:
        """Verifica si se cumplen las condiciones de consolidación."""
        if message_count >= 10:
            return True

        from src.memory.long_term_memory import long_term_memory

        buffer = await long_term_memory.get_buffer()
        last_activity = await buffer.get_last_activity(chat_id)

        if last_activity > 0:
            elapsed = time.time() - last_activity
            if elapsed > 1800:  # 30 minutos
                return True
        return False

    async def consolidate_session(self, chat_id: str) -> None:
        """Proceso completo de consolidación con Redis Lock anti-carreras."""
        from src.core import dependencies

        if dependencies.redis_connection is None:
            logger.warning("Redis no disponible. Saltando consolidación.")
            return

        lock_key = f"lock:consolidate:{chat_id}"
        # Intentar adquirir lock de inmediato
        lock = dependencies.redis_connection.lock(lock_key, timeout=60, blocking=False)
        acquired = await lock.acquire()
        if not acquired:
            logger.info(
                "Consolidación en curso para %s. Ignorando doble disparo.", chat_id
            )
            return

        try:
            logger.info("Consolidating session for %s", chat_id)
            from src.memory.fact_extractor import fact_extractor
            from src.memory.knowledge_base import knowledge_base_manager
            from src.memory.long_term_memory import long_term_memory

            buffer = await long_term_memory.get_buffer()
            raw_buffer = await buffer.get_messages(chat_id)
            if not raw_buffer:
                return

            await long_term_memory.update_memory(chat_id)

            try:
                cur_kb = await knowledge_base_manager.load_knowledge(chat_id)
                conv_text = "\n".join([
                    f"{m['role']}: {m['content']}" for m in raw_buffer
                ])
                upd_kb = await fact_extractor.extract_facts(conv_text, cur_kb)
                await knowledge_base_manager.save_knowledge(chat_id, upd_kb)
                await self._sync_user_name_to_profile(chat_id, upd_kb)
            except Exception as e:
                logger.error("Error facts consolidation %s: %s", chat_id, e)

            new_data = await long_term_memory.get_summary(chat_id)
            summary = new_data["summary"]

            # Guardar Nota Evolutiva extendida en Redis (ADR-0029 Complemento)
            try:
                if dependencies.redis_connection:
                    evo_key = f"chat:evolution_note:{chat_id}"
                    await dependencies.redis_connection.setex(
                        evo_key,
                        86400,  # TTL 24 horas
                        json.dumps(
                            {"summary": summary, "chat_id": chat_id}, ensure_ascii=False
                        ),
                    )
                    logger.debug(
                        "Evolution Note cached in Redis successfully for %s", chat_id
                    )
            except Exception as re:
                logger.warning("Error caching Evolution Note in Redis: %s", re)

            profile = await user_profile_manager.load_profile(chat_id)
            evolution = await self.evolution_detector.detect_evolution(profile, summary)
            if evolution:
                await apply_evolution(chat_id, profile, evolution)

            # 4. Learning Loop: Generación de Skills (ADR-0026)
            await self._check_for_new_skills(chat_id, summary)

            # 5. Generar aristas transversales (memory_edges) (ADR-0033) (Tarea 3.5)
            await self._generate_transversal_edges(chat_id, raw_buffer)

            await log_session_to_memory(chat_id, summary, len(raw_buffer))

        finally:
            await lock.release()

    async def _sync_user_name_to_profile(
        self, chat_id: str, knowledge: dict[str, Any]
    ) -> None:
        """Sincroniza el nombre detectado."""
        detected_name = knowledge.get("user_name")
        if not detected_name:
            return
        try:
            profile = await user_profile_manager.load_profile(chat_id)
            current_name = profile.get("identity", {}).get("name")
            if detected_name != current_name:
                logger.info("Sync Identity: %s -> %s", current_name, detected_name)
                profile["identity"]["name"] = detected_name
                await user_profile_manager.save_profile(chat_id, profile)
        except Exception as e:
            logger.error("Error syncing name %s: %s", chat_id, e)

    async def _check_for_new_skills(self, chat_id: str, summary: str) -> None:
        """Analiza si el resumen de la sesión amerita generar un nuevo skill."""
        # TODO: Implementar lógica de detección de dominios (heurística o LLM)
        # Por ahora es un stub que habilita la infraestructura de la Fase 7
        pass

    async def _generate_transversal_edges(
        self, chat_id: str, raw_buffer: list[dict]
    ) -> None:
        """
        Analiza las conversaciones e identifica relaciones causa/efecto o correlaciones transversales
        entre los hechos (facts) atómicos e inserta las aristas en la tabla memory_edges (ADR-0033).
        """
        try:
            from langchain_core.prompts import ChatPromptTemplate

            from src.core.dependencies import get_sqlite_store
            from src.core.llm_registry import get_llm

            # Solo operamos si hay suficientes hechos y el LLM está disponible
            store = get_sqlite_store()
            db = await store.get_db()

            # 1. Recuperar hechos atómicos del usuario del chat correspondiente
            sql = "SELECT id, content, metadata FROM memories WHERE chat_id = ? AND memory_type = 'fact' AND is_active = 1"
            async with db.execute(sql, (chat_id,)) as cursor:
                facts = await cursor.fetchall()
                if len(facts) < 2:
                    return  # Se necesitan al menos 2 hechos para establecer relaciones

            # Construir glosario de hechos candidatos
            facts_list = []
            facts_map = {}
            for r in facts:
                fid = r[0]
                content = r[1]
                meta = json.loads(r[2]) if isinstance(r[2], str) else r[2] or {}
                key = meta.get("fact_key", f"id_{fid}")
                facts_list.append({"id": fid, "key": key, "content": content})
                facts_map[key] = fid

            # Formatear hechos para el prompt
            facts_text = "\n".join([
                f"Hecho [{f['key']}]: '{f['content']}'" for f in facts_list
            ])

            # Formatear conversación
            conv_text = "\n".join([f"{m['role']}: {m['content']}" for m in raw_buffer])

            # 2. Diseñar el prompt estructurado
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    (
                        "Eres un experto analista cognitivo. Tu tarea es analizar una conversación "
                        "y una lista de hechos estructurados de un usuario, e identificar relaciones "
                        "de causa, correlación, refuerzo o contradicción entre ellos.\n"
                        "Usa únicamente los tipos de relación permitidos: 'correlaciona_con', 'causa', 'resuelve', 'contradice', 'refuerza'.\n"
                        "Devuelve exclusivamente un objeto JSON estructurado con la lista de aristas:\n"
                        '[{{"origen": "llave_hecho_1", "destino": "llave_hecho_2", "tipo": "causa", "peso": 0.85, "evidencia": "El usuario indica que..."}}]\n'
                        "No incluyas explicaciones, responde puramente con el JSON crudo."
                    ),
                ),
                (
                    "user",
                    (
                        "HECHOS DEL USUARIO:\n{facts_text}\n\n"
                        "CONVERSACIÓN DE LA SESIÓN:\n{conv_text}\n\n"
                        "Identifica las relaciones transversales:"
                    ),
                ),
            ])

            # 3. Invocar Gemini Flash (get_llm) para destilar el grafo
            llm_chain = prompt | get_llm("rag_fact_extraction")
            response = await llm_chain.ainvoke({
                "facts_text": facts_text,
                "conv_text": conv_text,
            })

            response_text = str(response.content).strip()
            if "```json" in response_text:
                response_text = (
                    response_text.split("```json")[1].split("```")[0].strip()
                )
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            edges = json.loads(response_text)
            if not isinstance(edges, list):
                return

            # 4. Insertar las aristas válidas en memory_edges de SQLite
            for item in edges:
                origen_key = item.get("origen")
                destino_key = item.get("destino")
                tipo = item.get("tipo")
                peso = item.get("peso", 1.0)
                evidencia = item.get("evidencia")

                # Resolver origen y destino
                origen_id = facts_map.get(origen_key)
                destino_id = facts_map.get(destino_key)

                if origen_id and destino_id and origen_id != destino_id:
                    # Insertar arista transversal
                    sql_insert = """
                        INSERT OR REPLACE INTO memory_edges
                        (origen_id, destino_id, tipo_relacion, peso, evidencia, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    await db.execute(
                        sql_insert,
                        (
                            origen_id,
                            destino_id,
                            tipo,
                            peso,
                            evidencia,
                            "consolidation_worker",
                        ),
                    )

            await db.commit()
            logger.info("Transversal memory edges created successfully for %s", chat_id)

        except Exception as e:
            logger.warning("Error generating transversal edges for %s: %s", chat_id, e)

    async def _adjust_edge_weights_from_feedback(
        self,
        store: Any,
        chat_id: str,
        conversation_history: list[dict],
        injected_graph_fragments: list[dict],
    ) -> dict:
        """
        El LLM evalua que fragmentos del grafo inyectados en el contexto
        fueron pertinentes. Los pesos de las aristas asociadas se refuerzan
        (+0.05) o se atenuan (-0.03).
        """
        if not injected_graph_fragments:
            return {"reinforced": 0, "decayed": 0}

        from src.core.llm_registry import get_llm

        fragments_text = "\n".join([
            f"- [{f.get('id', '?')}] {f.get('content', '')[:200]}"
            for f in injected_graph_fragments
        ])
        conv_text = "\n".join([
            f"{m.get('role', 'user')}: {m.get('content', '')[:300]}"
            for m in conversation_history[-20:]
        ])

        prompt = (
            "Analiza esta conversacion y los fragmentos de memoria del grafo "
            "que fueron inyectados en el contexto.\n"
            "Determina cuales fragmentos fueron SEMANTICAMENTE PERTINENTES "
            "al razonamiento de la conversacion.\n\n"
            f"CONVERSACION:\n{conv_text}\n\n"
            f"FRAGMENTOS:\n{fragments_text}\n\n"
            "Responde SOLO con un JSON: "
            '{"useful_ids": [lista de IDs de fragmentos utiles]}'
        )

        try:
            llm = get_llm("rag_fact_extraction")
            response = await llm.ainvoke(prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            start = content.find("{")
            end = content.rfind("}") + 1
            if start < 0 or end <= start:
                return {"reinforced": 0, "decayed": 0}

            import json

            data = json.loads(content[start:end])
            useful_ids = set(data.get("useful_ids", []))

            db = await store.get_db()
            reinforced = 0
            decayed = 0

            for frag in injected_graph_fragments:
                edge_id = frag.get("edge_id")
                if not edge_id:
                    continue
                frag_id = frag.get("id")
                if frag_id in useful_ids:
                    await db.execute(
                        "UPDATE memory_edges SET peso = MIN(2.0, peso + 0.05) "
                        "WHERE id = ?",
                        (edge_id,),
                    )
                    reinforced += 1
                else:
                    await db.execute(
                        "UPDATE memory_edges SET peso = MAX(0.0, peso - 0.03) "
                        "WHERE id = ?",
                        (edge_id,),
                    )
                    decayed += 1

            await db.commit()
            logger.info(
                "[FEEDBACK] chat=%s: %d/%d fragmentos utiles",
                chat_id,
                reinforced,
                len(injected_graph_fragments),
            )
            return {"reinforced": reinforced, "decayed": decayed}
        except Exception as e:
            logger.warning("[FEEDBACK] Error ajustando pesos: %s", e)
            return {"reinforced": 0, "decayed": 0}

    async def _detect_temporal_patterns(self, chat_id: str, store: Any) -> list[dict]:
        """
        Detecta patrones temporales en los facts del usuario.
        Agrupa por day_of_week y hour_of_day para encontrar
        correlaciones (ej. "los lunes reporta mas ansiedad").
        """
        import json

        db = await store.get_db()

        sql = """
            SELECT id, content, metadata FROM memories
            WHERE chat_id = ? AND memory_type IN ('fact', 'preference')
            AND is_active = 1 AND metadata LIKE '%"day_of_week"%'
            ORDER BY created_at DESC
            LIMIT 200
        """

        async with db.execute(sql, (chat_id,)) as cursor:
            rows = await cursor.fetchall()

        if len(rows) < 10:
            return []

        facts_by_day: dict[int, list[dict]] = {}
        for row in rows:
            try:
                meta = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                dow = meta.get("day_of_week")
                if dow is not None:
                    facts_by_day.setdefault(dow, []).append({
                        "id": row[0],
                        "content": row[1],
                        "metadata": meta,
                    })
            except Exception:
                continue

        patterns = []
        day_names = [
            "lunes",
            "martes",
            "miercoles",
            "jueves",
            "viernes",
            "sabado",
            "domingo",
        ]

        anxiety_keywords = [
            "ansied",
            "estres",
            "nervios",
            "angustia",
            "preocup",
            "miedo",
            "panico",
        ]
        energy_keywords = [
            "energia",
            "motiv",
            "entusias",
            "activo",
            "productiv",
            "bien",
            "mejor",
        ]

        for day, facts in facts_by_day.items():
            if len(facts) < 3:
                continue

            content_lower = " ".join(f["content"].lower() for f in facts)

            anxiety_count = sum(1 for kw in anxiety_keywords if kw in content_lower)
            energy_count = sum(1 for kw in energy_keywords if kw in content_lower)

            if anxiety_count >= 2:
                patterns.append({
                    "content": (
                        f"Patron detectado: el usuario reporta ansiedad "
                        f"con mas frecuencia los {day_names[day]}."
                    ),
                    "type": "temporal_pattern",
                    "confidence": 0.7,
                    "day_of_week": day,
                })

            if energy_count >= 2:
                patterns.append({
                    "content": (
                        f"Patron detectado: el usuario muestra mas energia "
                        f"los {day_names[day]}."
                    ),
                    "type": "temporal_pattern",
                    "confidence": 0.7,
                    "day_of_week": day,
                })

        return patterns


consolidation_manager = ConsolidationManager()
