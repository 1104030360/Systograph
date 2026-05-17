# AGENTS.md

## Project Context

KAI-Mind / Local AI Health Doctor is an AI Agent / RAG Release Readiness Gate. It scans existing local AI systems before demo, handoff, deployment, or CI/CD.

It is not a chatbot, RAG builder, full observability platform, or enterprise security scanner.

## Review Guidelines

- Focus on release-readiness regressions.
- Flag unsafe filesystem scanning, secret exposure, and network exposure risks.
- Scanner code must be read-only by default unless a task explicitly requires mutation.
- Do not print full secret values in logs, reports, test snapshots, or PR comments.
- Treat missing tests for scanner behavior as P1.
- Treat JSON report schema breakage as P1 unless migration is documented.
- Check that CLI behavior remains usable on Windows and macOS.
- Check that packaging code does not duplicate core scanner logic.
- Prefer evidence-based findings over single opaque scores.

## Development Guidelines

- Keep Core Engine behavior independent from platform launchers.
- Keep CLI and JSON report contracts stable.
- Make cross-platform assumptions explicit.
- Document uncertainty for network exposure checks.
- Use sample projects and fixtures for scanner tests.
