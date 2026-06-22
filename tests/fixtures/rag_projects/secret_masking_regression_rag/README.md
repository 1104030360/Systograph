# secret_masking_regression_rag

## Reference sources

- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- https://github.com/pypa/pip

## Scanner signals

- `.env.example` contains synthetic key variants and URL userinfo.
- `config.yaml` contains an OpenAI-compatible endpoint with URL userinfo.
- `requirements.txt` provides an external OpenAI provider signal.

## Safety notes

- This fixture does not require network access.
- This fixture does not include real secrets.
- Every credential value is synthetic test data for masking regressions.
