from typing import Literal

from pydantic import BaseModel, Field


class DocumentContent(BaseModel):
    """Define la estructura de un resultado de procesamiento de documento exitoso."""

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados

    type: Literal["document"] = "document"
    file_name: str = Field(..., description="El nombre original del archivo procesado.")
    content: str = Field(
        ..., description="El contenido de texto extraído del documento."
    )
    extension: str = Field(..., description="La extensión del archivo, ej: '.pdf'.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "document",
                    "file_name": "annual_report.docx",
                    "content": "This is the first paragraph...",
                    "extension": ".docx",
                }
            ]
        }
    }


class DocumentError(BaseModel):
    """Define la estructura para un error durante el procesamiento de un documento."""

    # TODO: Evaluar eliminación - sin consumidores activos externos detectados

    type: Literal["error"] = "error"
    file_name: str = Field(
        ..., description="El nombre del archivo que falló al procesar."
    )
    message: str = Field(..., description="El mensaje de error detallado.")
    extension: str = Field(
        ..., description="La extensión del archivo que causó el error."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "error",
                    "file_name": "corrupt.pdf",
                    "message": "El archivo PDF está corrupto o no se puede leer.",
                    "extension": ".pdf",
                }
            ]
        }
    }
