# Project Justification: vibecraft

## What Problem Does This Solve?
AI-assisted "vibe-coding" ( approving AI-generated code without deep review ) produces code that compiles but carries hidden quality traps: missing error handlers, magic constants, incomplete edge-case handling, and absent test coverage. Developers have no lightweight way to audit a file or diff for these patterns before PR review.

## Who Is the User?
- Developers using AI coding assistants (Copilot, Cursor, etc.) who want a second opinion on AI-generated code
- Tech leads reviewing AI-assisted PRs who need objective quality signals
- The Jarmes system itself (Forge) when evaluating code quality in its own builds

## Why Existing Solutions Are Inadequate
- **pre-commit-ai**: focused on formatting, not quality traps
- **CodeQL/Semgrep**: powerful but require query authoring; overkill for quick audit
- **Code climate**: SaaS, no CLI-first local audit
- **AST complexity tools**: only measure complexity, not the specific patterns of vibe-coding

No tool focuses specifically on the signature patterns of AI-generated code: over-reliance on utility libraries, under-documentation, edge-case negligence, and inconsistent naming.

## How We'll Know It's Successful
- `vibecraft analyze <file>` returns a craftsmanship score (0-100) in <1s
- Flags specific findings (missing error handlers, magic strings, etc.)
- Works as a CI gate: `vibecraft check --threshold 70` exits 1 if score < 70
- Forge uses it on its own output as a quality signal
