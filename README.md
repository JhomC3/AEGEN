# 🤖 AEGEN: Sistema de Agentes con Arquitectura Evolutiva

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AEGEN** es una plataforma robusta y escalable para construir y orquestar agentes de IA complejos. Su objetivo es procesar peticiones en lenguaje natural y ejecutar tareas complejas de forma autónoma.

## 📖 Manual del Proyecto

Toda la filosofía de desarrollo, los estándares de codificación, la guía de arquitectura, el estado actual y la hoja de ruta del proyecto se encuentran documentados en nuestro manual principal.

Este documento es de **lectura obligatoria** para cualquier contribuidor (humano o IA).

➡️ **[📄 Manual de Arquitectura y Desarrollo (PROJECT_OVERVIEW.md)](PROJECT_OVERVIEW.md)**

## ✨ Características Principales

- **Arquitectura Evolutiva:** Diseñado para pasar de un monolito a un sistema distribuido cuando sea necesario.
- **Desacoplamiento por Eventos:** Orquestación de flujos de trabajo a través de un bus de eventos asíncrono.
- **Observabilidad "Día Cero":** Logging estructurado, trazabilidad de peticiones y métricas Prometheus desde el inicio.
- **Resiliencia Integrada:** Mecanismos de reintentos e idempotencia para un procesamiento de tareas robusto.
- **Calidad de Código:** Pipeline de CI/CD con linters y chequeo de tipos (Ruff, Black, MyPy).

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose

### Instalación y Ejecución

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/JhomC3/aegen.git
    cd aegen
    ```

2.  **Configurar variables de entorno:**
    ```bash
    cp .env.example .env
    ```

3.  **Levantar los servicios:**
    ```bash
    make up
    ```

Una vez levantado, la documentación interactiva de la API estará disponible en [http://localhost:8000/docs](http://localhost:8000/docs).

---
