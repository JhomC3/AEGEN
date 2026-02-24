# AEGEN: De Chatbot a Sistema de Soporte Vital

AEGEN ha evolucionado de ser una interfaz de chat reactiva a un ecosistema proactivo de gestión de vida. Este documento resume los pilares arquitectónicos que sostienen esta nueva fase.

## 1. El Cerebro Dual (Dual Brain Architecture)
Para garantizar estabilidad y naturalidad, el sistema separa la inferencia en dos motores:
- **Motor Conversacional (MAGI-CHAT):** Optimizado para la calidez, empatía y el tuteo neutro. Usa modelos como Kimi K2.
- **Motor Estructural (MAGI-CORE):** Optimizado para la precisión técnica y la generación de JSON. Usa modelos masivos (120B) y prescinde de instrucciones de personalidad para evitar "fugas de chat".

## 2. Memoria Direccional y Estado (State Management)
AEGEN ya no solo recuerda hechos; rastrea el progreso mediante:
- **Metas (Goals):** Objetivos a largo plazo (Salud, Finanzas, Mental).
- **Hitos (Milestones):** Eventos específicos detectados automáticamente tras cada charla.
- **Life Reviewer:** Un worker de fondo que analiza tendencias longitudinales (ej. aumento de fuerza en el gimnasio o mejora del ánimo).

## 3. Agencia y Proactividad (Outbox Pattern)
El sistema ha roto el esquema reactivo (Usuario -> Bot). MAGI ahora tiene agencia propia:
- **Bandeja de Salida (Outbox):** Permite agendar mensajes para el futuro.
- **Inyección Suave de Intención:** Si el usuario habla antes de un mensaje programado, MAGI inyecta esa intención en su memoria para sacarla a colación de forma natural.

## 4. Escudo de Identidad (LinguaGuard)
Garantizamos una identidad lingüística coherente mediante:
- **Late Context Injection:** Inyección de reglas de tono justo antes de la respuesta del modelo para evitar el desvanecimiento de instrucciones en contextos largos.
- **Neutralización en Tiempo Real:** Un filtro de salida que intercepta regionalismos accidentales ("tío", "vos") y los corrige antes de que lleguen al usuario.

---
*Última actualización: 2026-02-24*
