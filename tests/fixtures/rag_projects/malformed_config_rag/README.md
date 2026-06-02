# malformed_config_rag

## Reference sources

- Project-owned malformed fixture for parser behavior.

## Scanner signals

- `docker-compose.yml` is intentionally malformed.
- `package.json` is intentionally malformed.
- The scanner should produce parse issue evidence instead of crashing.

## Safety notes

- This fixture does not require network or Docker.
- This fixture does not include real secrets.
- The invalid YAML is intentional test input.
