# src/agents/report_generator.py
import os

from core.config import settings
from core.schemas import ReportGenerationState
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from tools.stt_tool import speech_to_text_tool
from tools.youtube_tools import download_youtube_audio_tool, youtube_search_tool


class ReportGeneratorAgent:
    """
    Un agente con un flujo de trabajo fijo para generar un reporte consolidado
    a partir de múltiples videos de YouTube.
    """

    def __init__(self, llm):
        self.llm = llm
        self.graph = self._build_graph()

    def _find_videos(self, state: ReportGenerationState) -> dict:
        """Paso 1: Busca una lista de videos."""
        print("--- Paso 1: Buscando videos ---")
        query = state.original_query
        try:
            # Llama a la herramienta que ahora devuelve una lista de videos
            videos = youtube_search_tool.invoke({"query": query, "max_results": 3})
            print(f"Se encontraron {len(videos)} videos para procesar.")
            return {"videos_to_process": videos}
        except Exception as e:
            return {"error": f"Error al buscar videos: {e}"}

    def _process_videos_in_batch(self, state: ReportGenerationState) -> dict:
        """Paso 2: Itera sobre cada video para descargarlo y transcribirlo."""
        print("\n--- Paso 2: Procesando videos en lote ---")
        videos_to_process = state.videos_to_process
        transcripts = []
        audio_paths = []

        for video in videos_to_process:
            video_id = video["video_id"]
            video_title = video["title"]
            print(f"\nProcesando video: '{video_title}' (ID: {video_id})")
            try:
                # 2a: Descargar audio
                audio_path = download_youtube_audio_tool.invoke({"video_id": video_id})
                audio_paths.append(audio_path)

                # 2b: Transcribir audio
                transcript = speech_to_text_tool.invoke({"audio_path": audio_path})
                transcripts.append(
                    f"--- Transcripción de '{video_title}' ---\n{transcript}\n"
                )
            except Exception as e:
                print(f"No se pudo procesar el video '{video_title}': {e}")
                # Añadimos un marcador para saber que este video falló
                transcripts.append(
                    f"--- Transcripción de '{video_title}' (FALLIDO) ---\nError: {e}\n"
                )

        return {"transcripts": transcripts, "audio_file_paths": audio_paths}

    def _generate_consolidated_report(self, state: ReportGenerationState) -> dict:
        """Paso 3: Genera un único reporte a partir de todas las transcripciones."""
        print("\n--- Paso 3: Generando reporte consolidado ---")

        all_transcripts = "\n".join(state.transcripts)

        prompt = HumanMessage(
            content=f"""
            A partir de las siguientes transcripciones de varios videos relacionados con '{state.original_query}',
            crea un único reporte consolidado, coherente y bien estructurado.
            Sintetiza la información clave de todas las fuentes en un solo documento.
            Si alguna transcripción falló, menciónalo brevemente.

            Transcripciones:
            {all_transcripts}
            ---

            Por favor, genera el reporte consolidado ahora.
            """
        )

        response = self.llm.invoke([prompt])
        return {"report": response.content}

    def _cleanup_files(self, state: ReportGenerationState) -> dict:
        """Paso Final: Limpia todos los archivos de audio temporales."""
        print("\n--- Paso Final: Limpiando archivos temporales ---")
        for path in state.audio_file_paths:
            try:
                if path and os.path.exists(path):
                    temp_dir = os.path.dirname(path)
                    os.remove(path)
                    if not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
            except Exception as e:
                print(f"Advertencia: No se pudo limpiar el archivo {path}: {e}")
        return {}

    def _decide_next_step(self, state: ReportGenerationState) -> str:
        """
        Decide el siguiente paso basado en si ocurrió un error.
        """
        if state.error:
            print(f"\n--- Error detectado: {state.error} ---")
            # Si hay un error, vamos directamente a la limpieza para terminar
            return "cleanup"

        # Si no hay error, decide el siguiente paso normal en el pipeline
        if not state.transcripts:
            # Si aún no hay transcripciones, el siguiente paso es procesar el lote
            return "process_batch"

        # Si ya hay transcripciones, el siguiente paso es generar el reporte
        return "generate_report"

    def _build_graph(self):
        """
        Construye el grafo del pipeline con lógica condicional para manejar errores.
        """
        graph_builder = StateGraph(ReportGenerationState)

        # Añadir todos los nodos al grafo
        graph_builder.add_node("find_videos", self._find_videos)
        graph_builder.add_node("process_batch", self._process_videos_in_batch)
        graph_builder.add_node("generate_report", self._generate_consolidated_report)
        graph_builder.add_node("cleanup", self._cleanup_files)

        # El punto de entrada siempre es buscar videos
        graph_builder.add_edge(START, "find_videos")

        # Después de buscar, decidir si continuar o limpiar
        graph_builder.add_conditional_edges(
            "find_videos",
            self._decide_next_step,
            {
                "process_batch": "process_batch",  # Continuar si no hay error
                "cleanup": "cleanup",  # Ir a limpieza si hay error
            },
        )

        # Después de procesar el lote, decidir si continuar o limpiar
        graph_builder.add_conditional_edges(
            "process_batch",
            self._decide_next_step,
            {
                "generate_report": "generate_report",  # Continuar si no hay error
                "cleanup": "cleanup",  # Ir a limpieza si hay error
            },
        )

        # Después de generar el reporte, el siguiente paso es siempre la limpieza
        graph_builder.add_edge("generate_report", "cleanup")

        # El final del grafo es después de que el nodo de limpieza se ejecute
        graph_builder.add_edge("cleanup", END)

        return graph_builder.compile()

    def run(self, query: str):
        initial_state = {"original_query": query}
        final_state = self.graph.invoke(initial_state)

        if final_state.get("error"):
            print(f"\n--- El proceso falló: {final_state['error']} ---")
            return None

        print("\n\n--- REPORTE FINAL CONSOLIDADO ---")
        print(final_state.get("report", "No se generó ningún reporte."))
        return final_state.get("report")


def main():
    google_api_key = settings.GOOGLE_API_KEY.get_secret_value()
    os.environ["GOOGLE_API_KEY"] = google_api_key
    llm = init_chat_model("google_genai:gemini-2.5-flash")
    agent = ReportGeneratorAgent(llm=llm)

    print("Generador de Reportes de YouTube. Escribe 'q' para salir.")
    while True:
        try:
            user_input = input("Tema para el reporte (se buscarán 3 videos): ")
            if user_input.lower() in ["q", "quit", "exit"]:
                break
            agent.run(user_input)
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(f"\nOcurrió un error inesperado: {e}\n")
    print("\nAdiós.")


if __name__ == "__main__":
    main()
