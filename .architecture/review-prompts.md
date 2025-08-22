# Architecture Review Prompts

## Pre-Code Analysis Prompt
```
ANTES DE ESCRIBIR CÓDIGO, analiza este diseño usando Clean Architecture principles:

DISEÑO PROPUESTO:
[Describe what you want to build]

ANÁLISIS REQUERIDO:
1. **Single Responsibility:** ¿Cada componente tiene una sola responsabilidad?
2. **Dependencies:** ¿Se pueden inyectar vs construir internamente?
3. **Pure Functions:** ¿Qué lógica puede ser pure functions?
4. **Separation:** ¿Business logic separado de infrastructure?
5. **File Structure:** ¿Cómo dividir en archivos cohesivos?

RESULTADO ESPERADO:
- Lista de archivos con responsabilidades específicas
- Identificación de dependencies a inyectar
- Señalar potential violations antes de coding
```

## Code Review Prompt
```
REVISA este código contra Clean Architecture principles:

CÓDIGO:
[Paste code]

EVALUACIÓN:
1. **SRP Violations:** ¿Qué clases/funciones hacen demasiado?
2. **Coupling Issues:** ¿Dónde hay tight coupling?
3. **Pure Function Opportunities:** ¿Qué se puede extraer como pure functions?
4. **Dependency Issues:** ¿Qué dependencies se construyen vs se inyectan?
5. **Refactoring Suggestions:** Cambios específicos para mejorar architecture

FORMATO RESPUESTA:
- ✅ Lo que está bien
- 🚫 Violations específicas
- 🔧 Refactorings exactos a aplicar
```

## Architecture Decision Prompt
```
NECESITO decidir arquitectura para: [FEATURE]

CONTEXTO:
- Existing codebase: [Description]
- New requirements: [Requirements]
- Constraints: [Constraints]

EVALUACIÓN:
1. **Patterns:** ¿Qué architectural patterns aplicar?
2. **Structure:** ¿Cómo organizar files/directories?
3. **Dependencies:** ¿Qué dependencies necesito?
4. **Interfaces:** ¿Qué abstractions crear?
5. **Testing:** ¿Cómo hacer testeable?

RESULTADO:
- Specific architectural decisions
- File structure with responsibilities
- Dependency injection strategy
- Testing approach
```
