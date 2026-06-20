# EduGate — AI Access Gateway for Schools

## Problem
Norway just banned generative AI for students aged 6-13 (grades 1-7) and restricted supervised use for ages 14-16. This regulatory cascade is beginning globally — Australia banned social media under 16, the US Department of Education issued age-appropriate AI priorities, and Japan classifies AI-generated schoolwork as cheating. Schools need a technical enforcement layer, not just policy documents.

## Who Uses This
- **School IT administrators** who need to enforce district AI policies
- **Teachers** who need to supervise and monitor AI tool usage in their classrooms
- **Students** who interact with AI tools through a controlled gateway
- **Compliance officers** who need audit trails for regulatory reporting

## Why Existing Solutions Are Inadequate
Commercial K-12 AI platforms (LittleLit, SchoolAI, Teachfloor) are proprietary SaaS with per-student pricing. They don't enforce age-gated access policies — they provide curriculum content. There is no open-source tool that:
1. Enforces age/grade-based AI access policies at the network level
2. Provides teacher-supervised AI chat with real-time monitoring
3. Generates compliance reports for education regulators
4. Maintains per-student audit trails of AI interactions

## Success Criteria
- Schools can deploy EduGate as a self-hosted gateway
- Teachers can monitor student AI usage in real-time
- Compliance reports auto-generate for Norway's August 2026 regulations
- Zero external API dependencies for the gateway itself (works with any LLM provider)

## Tech Stack
- Python/FastAPI backend (server-rendered HTML, no Node.js build step)
- Jinja2 templates + vanilla JS for interactive features
- SQLite for audit logs and policy storage
- Age-gate policy engine with teacher override capability
