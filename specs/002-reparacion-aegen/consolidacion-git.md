# Consolidación Git — 2026-10-27

El dueño autorizó organizar los cambios pendientes de AEGEN, crear commits y
hacer push. No autoriza con ello despliegue, merge ni intervención en el
repositorio hermano de Entrenamiento, en sus procesos o en las bases vivas.

Rama de publicación: `codex/consolidacion-aegen-senda`, basada en `8d1f671`.
El índice estaba vacío al iniciar. El remoto verificado es `JhomC3/AEGEN`.
Identidad para autor y committer: `104508870+JhomC3@users.noreply.github.com`.

Unidades: exclusión de artefactos locales; reparación del recorrido AEGEN;
fuentes y documentación de la integración SENDA; habilidades de desarrollo.
Las fuentes actuales de SENDA se preservan como el corte ya transferido a este
repositorio; no se sincronizan con el checkout hermano ni se declara paridad
con sus cambios posteriores. Se conservan las decisiones y evidencias históricas
de spec 001, sin convertirlas en verificación actual de producción.

Se excluyen `.env`, DB, WAL, secretos, respaldos, `.tmp/`, SDK, build y paquetes
de entrega. Los artefactos locales se conservan, no se borran.

La reparación cuenta con 34 regresiones en la copia de la base de la VM más sus
13 archivos de fuente. Docker, Redis real y Telegram siguen pendientes. Push
no equivale a despliegue ni al cierre de la integración.

Se corrige el fixture del test de undo de bienestar: el mensaje usa la misma
fecha explícita del registro simulado, en lugar de «hoy». Evita que el test
dependa del calendario; no cambia conducta de producto ni excluye el test.

Los hooks conservan el mypy de AEGEN para sus fuentes y añaden un chequeo
completo separado de SENDA desde su directorio y con su configuración. Aplicar
el contrato Python 3.13/strict de AEGEN al dominio Python 3.11 producía 1846
errores ajenos al contrato del dominio; no se debilitan las reglas de ninguno.
Prerrequisito local: ambos entornos instalados (raíz y apps/entrenamiento).

Verificación de consolidación: 61 tests de API, skills, loader, memoria y
webhook aprobados; dominio sin e2e: 968 aprobados en sandbox y los tres casos de
lectura externa aprobados al repetir con red (10 tests en esa reejecución,
incluidos siete ya contados). Total distinto del dominio: 971. Mypy del dominio:
167 archivos sin errores. Los hooks pueden normalizar espacios e imports;
las correcciones de estilo se verifican con regresiones pertinentes.

Tras normalizar imports y formato del dominio se repitieron 107 tests de cardio,
resúmenes y seguridad: todos aprobados. La copia fuente Android corresponde al
corte histórico de SENDA, sin recompilar ni instalar APK en esta consolidación.

Las habilidades de desarrollo se guardan con su lock de procedencia. Sus dos
auxiliares CLI se adaptan a pathlib, logging y anotaciones de retorno para
cumplir los controles del repositorio, conservando su función y salida. No se
ejecutan contra datos operativos. El validador de estructura/configuración y
el auxiliar JSON se comprueban de forma directa.
