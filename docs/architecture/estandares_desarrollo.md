# Estándares de Desarrollo AEGEN

Este documento define la filosofía y las prácticas de ingeniería obligatorias para el proyecto, basadas en el Zen de Python y principios de Clean Architecture.

## 1. Filosofía de Python (Zen de Python)
Como guía fundamental, seguimos los principios de PEP 20:
- **Lo bello es mejor que lo feo.**
- **Explícito es mejor que implícito.**
- **Simple es mejor que complejo.**
- **Plano es mejor que anidado.**
- **La legibilidad cuenta.**

## 2. Límites de Complejidad (Regla 100/20)
Para mantener la agilidad evolutiva:
- **Archivos:** Máximo **100 líneas de código**. Si un archivo crece más, debe dividirse en submódulos lógicos.
- **Funciones/Métodos:** Máximo **20 líneas**. Si es más larga, extrae lógica a funciones privadas.
- **Clases:** Un solo propósito (SRP - Single Responsibility Principle). Máximo 7 métodos públicos.

## 3. Prácticas de Ingeniería
- **TDD (Test Driven Development):** Escribir la prueba antes del código siempre que sea posible.
- **Inyección de Dependencias:** No instanciar clientes (Redis, SQLite) dentro de las funciones; recibirlos como argumentos.
- **Inmutabilidad:** Preferir el paso de datos inmutables entre agentes.
- **Documentación Progresiva:** Documentar el *porqué* en el código y el *cómo* en `docs/architecture/`.

## 4. Gestión de Planes de Desarrollo
Para cada nueva funcionalidad, se debe crear un archivo en `docs/plans/` con:
1. **Objetivo claro.**
2. **Impacto en el sistema.**
3. **Pasos detallados de implementación (Bite-sized tasks).**
4. **Criterios de verificación (DoD).**

---
*Cualquier código que viole estos estándares será rechazado automáticamente por la suite de verificación.*
