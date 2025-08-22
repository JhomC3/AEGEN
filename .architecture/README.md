# AEGEN Architecture Standards

## 🎯 MANDATORY: Architecture-First Development

### Quick Start
1. **📋 BEFORE coding:** Read `pre-code-checklist.md`
2. **🤖 AI Review:** Use prompts from `review-prompts.md`
3. **📁 Follow Template:** Use `templates/specialist-template.md`
4. **🔄 Apply Workflow:** Follow `development-workflow.md`

### File Purpose
- `pre-code-checklist.md` - Checklist to use BEFORE writing ANY code
- `review-prompts.md` - AI prompts for architecture guidance
- `templates/` - Code templates following clean architecture
- `development-workflow.md` - Step-by-step process for all development

### Core Principles
1. **Single Responsibility:** One reason to change per class/file
2. **Dependency Injection:** Dependencies injected, not constructed
3. **Pure Functions:** No side effects where possible
4. **Separation of Concerns:** Business logic ≠ infrastructure
5. **Clean File Structure:** < 100 lines per file, clear naming

### Quality Gates
- ✅ All checklist items pass
- ✅ Can unit test each component independently
- ✅ Easy to extend without modification
- ✅ Clear separation of responsibilities

## 🚨 THIS IS NOW THE STANDARD

**Every piece of code must follow this process.**
**No exceptions. No shortcuts.**
**Quality first, speed second.**

### Need Help?
1. Check templates first
2. Use AI review prompts
3. Apply the checklist
4. Follow the workflow

**Architecture excellence is not optional - it's mandatory.**
