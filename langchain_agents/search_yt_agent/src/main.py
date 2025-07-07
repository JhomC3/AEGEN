import os
import sys  # Para poder imprimir a stdout/stderr y verlo en los logs de Docker

from googleapiclient.discovery import build
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

print("Iniciando agente LangChain...")

# --- Configuración de API Keys ---
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

if not YOUTUBE_API_KEY:
    print(
        "Advertencia: La variable de entorno YOUTUBE_API_KEY no está configurada. La herramienta de YouTube fallará.",
        file=sys.stderr,
    )
    # No salimos, pero la herramienta no funcionará


# --- Definición de Herramientas ---
@tool
def search_youtube(query: str) -> str:
    """Searches YouTube for videos based on a query and returns the top 3 results."""
    print(f"Ejecutando herramienta search_youtube con query: {query}")
    if not YOUTUBE_API_KEY:
        return "Error: YouTube API Key not configured."
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        search_response = (
            youtube.search()
            .list(q=query, part="snippet", maxResults=3, type="video")
            .execute()
        )

        results = []
        for item in search_response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            results.append(
                f"Title: {title}, URL: https://www.youtube.com/watch?v={video_id}"
            )

        output = "\n".join(results) if results else "No results found."
        print(f"Resultado de search_youtube: {output}")
        return output
    except Exception as e:
        error_msg = f"Error searching YouTube: {e}"
        print(error_msg, file=sys.stderr)
        return error_msg


# --- Configuración del LLM (Gemini) ---
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash"
    )  # O el modelo Gemini que prefieras
    print("LLM de Gemini configurado correctamente.")
except Exception as e:
    print(f"Error al configurar el LLM de Gemini: {e}", file=sys.stderr)
    sys.exit(1)

# --- Creación del Agente ---
tools = [search_youtube]
# Usamos un prompt estándar para agentes tipo ReAct (Reasoning and Acting)
try:
    prompt = hub.pull("hwchase17/react")
    print("Prompt de agente cargado correctamente.")
except Exception as e:
    print(f"Error al cargar el prompt del agente: {e}", file=sys.stderr)
    sys.exit(1)

try:
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
    )
    print("Agente y ejecutor creados correctamente.")
except Exception as e:
    print(f"Error al crear el agente o el ejecutor: {e}", file=sys.stderr)
    sys.exit(1)

# --- Lógica Principal (Ejemplo: procesar una entrada fija) ---
# En una aplicación real, aquí podrías tener un servidor web (FastAPI, Flask)
# o leer entradas de alguna otra fuente. Por ahora, solo ejecutamos una consulta.
print("Ejecutando consulta de ejemplo...")
try:
    # query_input = "Busca videos en YouTube sobre la API de Gemini de Google"
    query_input = (
        "Quien es el presidente de Colombia?"  # Ejemplo sin usar la herramienta
    )
    response = agent_executor.invoke({"input": query_input})
    print("\n--- Respuesta Final del Agente ---")
    print(response.get("output", "No se obtuvo respuesta."))
    print("---------------------------------")

except Exception as e:
    print(f"\nError durante la ejecución del agente: {e}", file=sys.stderr)

print("Script del agente finalizado.")
