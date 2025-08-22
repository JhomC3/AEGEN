# Architecture-First Development Workflow

## 🚀 MANDATORY PROCESS - Usar para TODO código nuevo

### Phase 1: Architecture Analysis (BEFORE coding)
1. **📋 Apply Pre-Code Checklist**
   - Read: `.architecture/pre-code-checklist.md`
   - Document decisions for each item

2. **🤖 AI Architecture Review**
   - Use prompts from `.architecture/review-prompts.md`
   - Get architectural guidance BEFORE writing code

3. **📁 Plan File Structure**
   - Use templates from `.architecture/templates/`
   - Define each file's single responsibility
   - Plan dependency injection points

### Phase 2: Implementation (DURING coding)
1. **📝 Follow Templates**
   - Start with template structure
   - Implement one file at a time
   - Keep each file < 100 lines

2. **✅ Continuous Validation**
   - After each file, check against checklist
   - If any item fails → refactor immediately
   - Don't accumulate technical debt

3. **🧪 Test as You Go**
   - Write unit tests for pure functions first
   - Test each component independently
   - Validate dependency injection works

### Phase 3: Review (AFTER coding)
1. **🔍 Architecture Review**
   - Apply code review prompt
   - Identify any remaining violations
   - Document architectural decisions

2. **🔧 Refactor if Needed**
   - Fix any identified issues
   - Ensure all checklist items pass
   - Update documentation

3. **📚 Learn & Document**
   - What worked well?
   - What patterns to reuse?
   - Update templates if needed

## 🚫 STOP CONDITIONS - Immediate refactor required

### Red Flags
- File > 100 lines
- Function > 20 lines
- Class with multiple responsibilities
- Dependencies constructed vs injected
- Business logic mixed with infrastructure
- Cannot easily unit test

### Quality Gates
- ✅ All checklist items pass
- ✅ Each file has single responsibility
- ✅ Pure functions where possible
- ✅ Dependencies injected
- ✅ Easy to unit test

## 📊 Success Metrics

### Code Quality
- Files: < 100 lines each
- Functions: < 20 lines each
- Classes: Single responsibility
- Dependencies: Injected, not constructed

### Architecture Health
- Coupling: Low between modules
- Cohesion: High within modules
- Testability: Each unit testable independently
- Flexibility: Easy to extend without modification

## 🎯 IMMEDIATE ACTION

**For EVERY new code:**
1. Read checklist FIRST
2. Use AI review prompts
3. Follow templates
4. Apply workflow phases
5. Don't skip ANY step

**This is now THE STANDARD WAY to develop in AEGEN.**
