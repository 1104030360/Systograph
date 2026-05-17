# Cross-Platform Strategy

## Decision

Do not build KAI-Mind as a Windows-only `.exe`.

Build the product around a shared Core Engine and CLI. The Windows `.exe`, macOS app, Local Web UI, and CI integration should all call the same core behavior.

## Recommended Architecture

```text
KAI-Mind
+-- Core Engine
|   +-- scanners
|   +-- checkers
|   +-- risk engine
|   +-- report generator
+-- CLI
|   +-- kai-mind scan
|   +-- kai-mind gate --ci
+-- Local Backend
|   +-- exposes scan/report APIs to localhost
+-- Local Web UI
|   +-- dashboard for selecting project folder and viewing report
+-- Platform Launchers
    +-- Windows: .exe
    +-- macOS: .app / .dmg
    +-- Linux: binary or AppImage
```

## Why Local Web UI Is Still Safe for Data Access

A pure browser app cannot safely and reliably scan local project folders, `.env` files, Docker state, ports, and running services because browser filesystem access is restricted.

A Local Web UI is different:

- The UI runs in the browser at `localhost`.
- A local backend or CLI performs the actual scan.
- The scanner reads only user-selected folders or explicitly configured targets.
- Reports are generated locally by default.

This means switching from `.exe only` to Local Web UI does not weaken the scanner. It makes the product cross-platform while keeping the sensitive work local.

## Suggested MVP Stack

- Core / CLI: Python
- Local API: FastAPI
- Web UI: React or another lightweight frontend
- Packaging later: Tauri or Electron launcher
- CI: GitHub Actions using the CLI

## Guardrails

- Scanners must be read-only by default.
- Do not print full secret values.
- Network checks should be shallow and explain uncertainty.
- `0.0.0.0` should be reported as possible exposure, not automatically as internet exposure.
- Keep launcher code thin; do not duplicate scanner logic inside platform-specific packages.

## Practical Team Workflow

Windows and macOS developers should both be able to run:

```bash
kai-mind scan --project ./sample-ai-stack --output report.json
kai-mind gate --ci
```

The launcher is only convenience. The CLI is the real contract.
