# Systograph hard cutover

Date: 2026-07-28

Systograph is the only supported product and technical identity after this
change. The migration intentionally does not provide compatibility aliases.

## Canonical identifiers

| Surface | Identifier |
| --- | --- |
| GitHub repository | `1104030360/Systograph` |
| Python distribution | `systograph` |
| Python import | `systograph` |
| CLI | `systograph` |
| State environment variable | `SYSTOGRAPH_STATE_DIR` |
| Default state directory | `~/.systograph` |
| Per-project trace configuration | `[tool.systograph.trace]` |
| Schema authority | `https://systograph.local/schemas/` |

## Breaking behavior

- Pre-cutover Python imports and CLI commands are unavailable.
- Pre-cutover environment variables and tool configuration tables are ignored.
- State created under a pre-cutover default directory is not auto-discovered.
- Schema IDs use the Systograph authority even when the artifact payload
  schema version remains unchanged.
- Scripts, CI jobs, launchers, integrations, and local environment files must
  use the canonical identifiers above.

## Local upgrade

1. Pull the cutover commit.
2. Run `uv sync` so the editable distribution and console script are rebuilt.
3. Set `SYSTOGRAPH_STATE_DIR` explicitly if durable state must live outside
   `~/.systograph`.
4. Re-import or re-scan projects whose state was created by a pre-cutover
   release. There is no implicit state-directory fallback.
5. Update scanned-project trace configuration to
   `[tool.systograph.trace]`.
6. Run `uv run systograph --help` to verify the active CLI.

The artifact payload versions such as `ai-system-map/v1` and
`ai-system-map/v2` are domain contract versions; they are not product names
and remain unchanged.
