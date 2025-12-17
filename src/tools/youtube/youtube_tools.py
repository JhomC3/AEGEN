# src/tools/youtube_tools.py
from __future__ import annotations

import os
import tempfile
from typing import Any

import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

from core.config import settings


@tool
def youtube_search_tool(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """
    Busca los videos más relevantes en YouTube para una consulta y devuelve
    una lista de videos, cada uno con su ID, título y URL.
    """
    print(
        f"Herramienta de Búsqueda: Buscando los {max_results} videos más relevantes para '{query}'..."
    )
    if not 1 <= max_results <= 50:
        raise ValueError("max_results debe estar entre 1 y 50.")

    try:
        api_key = settings.YOUTUBE_API_KEY.get_secret_value()
        youtube = build("youtube", "v3", developerKey=api_key)

        search_request = youtube.search().list(
            part="snippet",
            q=query,
            maxResults=max_results,
            type="video",
            order="relevance",
        )
        response = search_request.execute()
        items = response.get("items", [])

        if not items:
            print(f"No se encontraron videos para la búsqueda: '{query}'")
            return []

        video_list = []
        for item in items:
            video_id = item["id"]["videoId"]
            video_title = item["snippet"]["title"]
            video_list.append({
                "video_id": video_id,
                "title": video_title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

        print(f"Herramienta de Búsqueda: Se encontraron {len(video_list)} videos.")
        return video_list

    except HttpError as e:
        error_message = (
            f"Error en la API de YouTube: {e.resp.status}, {e.content.decode('utf-8')}"
        )
        print(f"Herramienta de Búsqueda: {error_message}")
        raise e
    except Exception as e:
        error_message = f"Ocurrió un error inesperado al buscar en YouTube: {e}"
        print(f"Herramienta de Búsqueda: {error_message}")
        raise e


@tool
def download_youtube_audio_tool(video_id: str) -> str:
    """
    Toma un ID de video de YouTube, descarga solo el audio usando yt-dlp
    a una ruta temporal y devuelve la ruta absoluta a ese archivo de audio.
    La limpieza del archivo debe ser manejada por el llamador.
    """
    print(f"Herramienta de Descarga (yt-dlp): Procesando video ID: {video_id}")

    temp_dir = tempfile.mkdtemp()
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(
                f"Herramienta de Descarga (yt-dlp): Descargando y extrayendo audio para {video_url}..."
            )
            ydl.download([video_url])
            audio_path = os.path.join(temp_dir, f"{video_id}.mp3")
            if not os.path.exists(audio_path):
                raise RuntimeError(
                    "El archivo de audio no se creó después de la descarga."
                )

        print(f"Herramienta de Descarga (yt-dlp): Audio descargado en: {audio_path}")
        return audio_path

    except Exception as e:
        if "temp_dir" in locals() and os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        error_message = f"Ocurrió un error al descargar el audio con yt-dlp para el video ID {video_id}: {e}"
        print(f"Herramienta de Descarga (yt-dlp): {error_message}")
        raise e
