# Coding Best Practices

**Status:** 📋 Planned (not yet documented)

This category will contain best practices for code quality, patterns, and style.

## Planned Topics

### Python Style & Conventions
- Project-specific coding standards
- Naming conventions (modules, classes, functions, variables)
- Import organization and structure
- Type hints and validation patterns
- Docstring standards (module, class, function)

### Module Design Patterns
- Module architecture (how to structure new modules)
- Class design patterns used in Ludi-Bot
- Function composition and reusability
- Singleton patterns and when to use them
- Module communication contracts

### Error Handling Standards
- Exception handling patterns
- Silent failure prevention (never bare `except: pass`)
- Error logging best practices
- When to fail loudly vs gracefully degrade
- Error message formatting

### Code Organization
- File and directory structure
- Where to put utilities vs modules vs scripts
- When to create a new file vs extend existing
- Module interdependencies and circular import prevention

### Documentation Standards
- When to write comments (and when not to)
- Docstring templates for functions and classes
- Inline comment best practices
- README templates for new modules

### Common Anti-Patterns to Avoid
- Hard-coded values that should be configurable
- Duplicate code that should be extracted
- Functions doing too much (single responsibility)
- Unclear naming (abbreviations, vague names)
- Missing error handling or validation

## Lessons to Document

As you discover coding patterns that work well (or don't), document them here:
- ✅ What worked well and why
- ❌ What didn't work and how it was fixed
- 🔧 Refactoring patterns that improved code quality
- 📝 Code review feedback that became standards

## Future Skill

**`/code-review`** - Automated code quality check
- Validates against project coding standards
- Checks for common anti-patterns
- Suggests improvements based on best practices
- Generates: compliance report + refactoring recommendations
