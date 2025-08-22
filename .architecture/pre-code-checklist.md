# Pre-Code Architecture Checklist ✅

**USAR ANTES DE ESCRIBIR CUALQUIER CÓDIGO**

## 🎯 Single Responsibility Principle
- [ ] ¿Esta clase/función hace UNA sola cosa?
- [ ] ¿Tiene una sola razón para cambiar?
- [ ] ¿Puedo describir su responsabilidad en 1 frase sin "Y"?
- [ ] ¿El nombre refleja claramente su única responsabilidad?

## 🔗 Dependencies & Coupling
- [ ] ¿Está inyectando dependencies vs construyéndolas?
- [ ] ¿Las dependencies son abstractions vs concrete implementations?
- [ ] ¿Puede testearse independientemente?
- [ ] ¿Evita import circular dependencies?

## 🏗️ Clean Architecture
- [ ] ¿Business logic separado de infrastructure?
- [ ] ¿Prompts/config en archivos separados?
- [ ] ¿Pure functions donde sea posible?
- [ ] ¿UI/API separado de core logic?

## 📁 File Organization
- [ ] ¿Cada archivo tiene < 100 líneas?
- [ ] ¿Naming claro y descriptivo?
- [ ] ¿Directory structure refleja responsabilidades?
- [ ] ¿Un archivo por class/concept?

## 🚫 Red Flags - STOP si ves:
- [ ] Clases con múltiples responsabilidades
- [ ] Métodos con > 20 líneas
- [ ] Múltiples if/else branches complejos
- [ ] Dependencies construidas vs inyectadas
- [ ] Mixing business logic con infrastructure

## ✅ Quality Gates
- [ ] ¿Es fácil de testear unitariamente?
- [ ] ¿Es fácil de extender sin modificar?
- [ ] ¿Es fácil de entender leyendo el código?
- [ ] ¿Sigue las convenciones del proyecto?

**SI ALGÚN ITEM NO PASA → REFACTOR ANTES DE CONTINUAR**
