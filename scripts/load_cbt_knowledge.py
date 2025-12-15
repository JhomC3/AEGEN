#!/usr/bin/env python3
"""
Script para cargar conocimiento CBT a la global knowledge base.

Uso:
    python scripts/load_cbt_knowledge.py
    
    # O especificar archivo personalizado:
    python scripts/load_cbt_knowledge.py --file cbt_data.json
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

# Agregar directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.dependencies import get_global_collection_manager

logger = logging.getLogger(__name__)

# Conocimiento CBT predefinido
CBT_KNOWLEDGE_BASE = [
    {
        "content": "La reestructuración cognitiva es una técnica fundamental de CBT que ayuda a identificar y cambiar pensamientos automáticos negativos. Los pasos incluyen: 1) Identificar pensamientos automáticos, 2) Evaluar la evidencia a favor y en contra, 3) Generar pensamientos alternativos más balanceados y realistas, 4) Practicar los nuevos pensamientos en situaciones reales.",
        "metadata": {
            "topic": "cbt_cognitive_restructuring",
            "category": "core_techniques",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Registro de pensamientos automáticos: Técnica para identificar y analizar pensamientos que aparecen automáticamente en situaciones problemáticas. Columnas: Situación, Emoción (0-10), Pensamiento automático, Evidencia a favor, Evidencia en contra, Pensamiento balanceado, Nueva emoción (0-10).",
        "metadata": {
            "topic": "cbt_thought_record",
            "category": "assessment_tools",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Técnicas de respiración para ansiedad: 1) Respiración diafragmática - colocar una mano en pecho, otra en abdomen, respirar lentamente haciendo que se mueva solo la mano del abdomen. 2) Respiración 4-7-8: inhalar por 4, mantener por 7, exhalar por 8. 3) Respiración cuadrada: inhalar 4, mantener 4, exhalar 4, mantener 4.",
        "metadata": {
            "topic": "cbt_breathing_techniques",
            "category": "anxiety_management",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Exposición gradual para fobias y ansiedad: Crear jerarquía de situaciones temidas del 1-10, comenzar con situaciones de bajo nivel de ansiedad (2-3), practicar hasta que la ansiedad disminuya significativamente, luego avanzar al siguiente nivel. Principio: la ansiedad naturalmente disminuye con exposición prolongada (habituación).",
        "metadata": {
            "topic": "cbt_exposure_therapy",
            "category": "anxiety_treatment",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Activación conductual para depresión: Programar actividades placenteras y de logro. Usar escala de placer (P) y logro (L) del 0-10. Comenzar con actividades pequeñas y alcanzables. Principio: el comportamiento influye en el estado de ánimo, la acción puede preceder a la motivación.",
        "metadata": {
            "topic": "cbt_behavioral_activation",
            "category": "depression_treatment",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Distorsiones cognitivas comunes: 1) Pensamiento todo-o-nada, 2) Sobregeneralización, 3) Filtro mental, 4) Descalificar lo positivo, 5) Conclusiones apresuradas (lectura mental/adivinación), 6) Magnificación/minimización, 7) Razonamiento emocional, 8) Declaraciones 'debería', 9) Etiquetado, 10) Personalización.",
        "metadata": {
            "topic": "cbt_cognitive_distortions",
            "category": "cognitive_patterns",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Técnicas de mindfulness en CBT: 1) Observación sin juicio del momento presente, 2) Respiración consciente, 3) Escaneo corporal, 4) Mindfulness de pensamientos (observar como nubes que pasan), 5) Aceptación radical. Objetivo: desarrollar conciencia metacognitiva y reducir rumiación.",
        "metadata": {
            "topic": "cbt_mindfulness",
            "category": "mindfulness_techniques",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Resolución de problemas estructurada: 1) Definir el problema específicamente, 2) Establecer metas realistas, 3) Generar múltiples soluciones (lluvia de ideas), 4) Evaluar pros y contras, 5) Seleccionar mejor opción, 6) Implementar plan de acción, 7) Evaluar resultados y ajustar si necesario.",
        "metadata": {
            "topic": "cbt_problem_solving",
            "category": "coping_strategies",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Manejo de ataques de pánico: 1) Reconocer síntomas físicos como normales y temporales, 2) Respiración lenta y controlada, 3) Técnica 5-4-3-2-1 (5 cosas que ves, 4 que oyes, 3 que tocas, 2 que hueles, 1 que saboreas), 4) Recordar que el pánico alcanza pico en 10 minutos y disminuye, 5) No huir de la situación.",
        "metadata": {
            "topic": "cbt_panic_management",
            "category": "crisis_intervention",
            "source": "cbt_manual",
            "language": "es"
        }
    },
    {
        "content": "Prevención de recaídas en CBT: 1) Identificar señales de alerta temprana, 2) Plan de acción específico para crisis, 3) Práctica regular de técnicas aprendidas, 4) Mantener rutinas saludables, 5) Red de apoyo social, 6) Seguimiento periódico con terapeuta, 7) Tarjetas de recordatorio con estrategias clave.",
        "metadata": {
            "topic": "cbt_relapse_prevention",
            "category": "maintenance_strategies",
            "source": "cbt_manual",
            "language": "es"
        }
    }
]

async def load_cbt_knowledge(knowledge_data: List[Dict[str, Any]] = None):
    """
    Carga conocimiento CBT a la global knowledge base.
    
    Args:
        knowledge_data: Lista de documentos CBT. Si None, usa CBT_KNOWLEDGE_BASE predefinido.
    """
    if knowledge_data is None:
        knowledge_data = CBT_KNOWLEDGE_BASE
    
    try:
        # Obtener manager de colecciones globales
        global_manager = get_global_collection_manager()
        
        print(f"🧠 Cargando {len(knowledge_data)} documentos CBT...")
        
        success_count = 0
        for i, item in enumerate(knowledge_data, 1):
            try:
                # Contribuir a la global knowledge base
                result = await global_manager.contribute_to_global_collection(
                    collection_name="global_knowledge_base",
                    content=item["content"],
                    metadata=item["metadata"],
                    user_id="cbt_knowledge_loader"
                )
                
                if result.get("success", False):
                    success_count += 1
                    print(f"✅ {i}/{len(knowledge_data)} - {item['metadata']['topic']}")
                else:
                    print(f"❌ {i}/{len(knowledge_data)} - Error: {result.get('error', 'Unknown')}")
                    
            except Exception as e:
                print(f"❌ {i}/{len(knowledge_data)} - Exception: {e}")
        
        print(f"\n🎉 Carga completada: {success_count}/{len(knowledge_data)} documentos cargados exitosamente")
        
        # Verificar que se cargaron correctamente
        test_query = await global_manager.query_global_collection(
            collection_name="global_knowledge_base",
            query_text="reestructuración cognitiva CBT",
            user_id="test",
            n_results=3
        )
        
        print(f"\n🔍 Verificación: encontrados {len(test_query)} documentos para 'reestructuración cognitiva'")
        
    except Exception as e:
        print(f"❌ Error cargando conocimiento CBT: {e}")
        raise

async def load_from_file(file_path: str):
    """Carga conocimiento CBT desde archivo JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            knowledge_data = json.load(f)
        
        if not isinstance(knowledge_data, list):
            raise ValueError("El archivo debe contener una lista de documentos")
        
        await load_cbt_knowledge(knowledge_data)
        
    except Exception as e:
        print(f"❌ Error cargando desde archivo {file_path}: {e}")
        raise

def create_sample_file(file_path: str = "cbt_knowledge_sample.json"):
    """Crea archivo de ejemplo con formato correcto."""
    sample_data = CBT_KNOWLEDGE_BASE[:3]  # Primeros 3 elementos como ejemplo
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Archivo de ejemplo creado: {file_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cargar conocimiento CBT a la global knowledge base")
    parser.add_argument("--file", type=str, help="Archivo JSON con conocimiento CBT")
    parser.add_argument("--create-sample", action="store_true", help="Crear archivo de ejemplo")
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_file()
    elif args.file:
        asyncio.run(load_from_file(args.file))
    else:
        asyncio.run(load_cbt_knowledge())