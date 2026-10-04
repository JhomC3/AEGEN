# Constitución — AEGEN

Principios de producto y arquitectura. El proceso SDD común vive en
`../../sdd-kit/SDD_BOOTSTRAP.md`; esta constitución no lo repite ni lo sustituye.

1. **Arquitectura evolutiva**: de monolito funcional a sistema distribuido solo
   cuando las métricas lo justifiquen.
2. **Simplicidad demostrable**: complejidad solo con necesidad y beneficio
   demostrables; sin umbrales inventados ni automatización universal.
3. **Contratos explícitos**: eventos (`CanonicalEventV1`), schemas Pydantic e
   interfaces como lenguaje común; cambios de contrato con impacto y tests.
4. **Datos seguros**: procedencia, confianza y evidencia; nada de datos reales,
   secretos o teléfonos vivos en git, docs, tests o ejemplos.
5. **Evidencia antes que afirmación**: validación veraz por requisito; el mensaje
   final de una suite no es garantía si su configuración oculta fallos.
6. **Observabilidad apropiada al riesgo**: métricas y trazas en flujos críticos
   (orquestación, memoria, mensajería); sin observabilidad universal obligatoria
   como puerta para todo cambio.
7. **Criterio propio**: ver método común §0 (bloqueante = detenerse;
   advertencia/sugerencia = alternativa + confirmación; disenso registrado en la spec).
