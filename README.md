# 🤖 AEGEN: Sistema de Agentes con Arquitectura Evolutiva

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AEGEN** es una plataforma robusta y escalable para construir y orquestar agentes de IA complejos. Su objetivo es procesar peticiones en lenguaje natural y ejecutar tareas complejas de forma autónoma.

## 📖 Manual del Proyecto

Toda la filosofía de desarrollo, los estándares de codificación, la guía de arquitectura, el estado actual y la hoja de ruta del proyecto se encuentran documentados en nuestro manual principal y carpetas especializadas.

Este documento es de **lectura obligatoria** para cualquier contribuidor (humano o IA).

1.  **[📄 Constitución (PROJECT_OVERVIEW.md)](PROJECT_OVERVIEW.md)**: Visión, arquitectura de alto nivel y Roadmap.
2.  **[📂 Arquitectura (docs/architecture/)](docs/architecture/)**: Detalle de subsistemas (Memoria, Personalidad, etc.).
3.  **[📂 Guías (docs/guides/)](docs/guides/)**: Instalación, Despliegue y Desarrollo.
4.  **[📜 Decisiones (adr/)](adr/)**: Registro histórico de decisiones técnicas.
5.  **[⚖️ Ley Técnica (rules.md)](rules.md)**: Estándares de código y seguridad.
6.  **[🤖 Gobernanza (AGENTS.md)](AGENTS.md)**: Reglas para agentes de IA.

## ✨ Características Principales

- **Arquitectura Evolutiva:** Diseñado para pasar de un monolito a un sistema distribuido cuando sea necesario.
- **Desacoplamiento por Eventos:** Orquestación de flujos de trabajo a través de un bus de eventos asíncrono.
- **Personalidad Adaptativa y Localización:** MAGI posee una identidad base que se adapta al estilo del usuario y a su localización regional (jerga, zona horaria) de forma automática.
- **Observabilidad LLM Completa:** Sistema híbrido LangSmith + Prometheus con tracking de llamadas, latency, tokens y costos. Correlation IDs end-to-end y dashboard tiempo real.
- **Agentes Modulares Multi-tenant:** Sistema de agentes componibles con aislamiento per-usuario y memoria híbrida (Redis + SQLite-vec).
- **Memoria Local-First:** Búsqueda semántica de baja latencia (<10ms) mediante `sqlite-vec` y búsqueda por palabras clave con `FTS5`.
- **Performance Optimizado:** Routing inteligente <2s, delegación híbrida, function calling optimizado (ADR-0009).
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
    make run-dev
    ```

Una vez levantado, la documentación interactiva de la API estará disponible en [http://localhost:8000/docs](http://localhost:8000/docs).

---
