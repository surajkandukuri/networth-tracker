# Repository Guidelines

## Project Structure & Module Organization
- `networth_tracker/` holds the Python package (email template, chart, market fetch, Gmail API, config helpers).
- `quarterly_run.py` is the local entrypoint that calls `networth_tracker.main.run()`.
- `config.yaml` drives runtime behavior (timezone, dry-run, real estate inputs, chart series).
- `tools/` contains one-off OAuth helpers (refresh-token script + dev requirements).
- `.github/workflows/quarterly.yml` defines the scheduled GitHub Actions run.
- Generated outputs (e.g., `snapshots/latest.json`) are created at runtime and should not be committed unless explicitly requested.

## Build, Test, and Development Commands
Install runtime dependencies:
```bash
python -m pip install -r requirements.txt
```
Run locally:
```bash
python quarterly_run.py
```
Dry run (no email send):
```bash
DRY_RUN=1 python quarterly_run.py
# or set run.dry_run: true in config.yaml
```
Generate a Gmail OAuth refresh token (one-time setup):
```bash
python -m pip install -r tools/requirements-dev.txt
python tools/get_refresh_token.py --client-secrets /path/to/client_secret.json
```

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, and type hints where practical.
- Use `snake_case` for modules/functions and `UPPER_SNAKE_CASE` for constants.
- Keep the “Email #2” HTML structure stable; avoid refactors that change layout unless explicitly requested.

## Testing Guidelines
- No automated test suite is configured in this repo today.
- Validate changes by running `python quarterly_run.py` with `DRY_RUN=1` and verifying the printed HTML output and chart rendering.
- If you add tests, use `tests/` with `test_*.py` naming and document any new framework in `requirements.txt`.

## Commit & Pull Request Guidelines
- Commit messages follow short, imperative sentence-case (e.g., “Refactor build_email_html function”).
- PRs should include: a concise description, linked issue (if any), and notes on config or output changes.
- Never commit secrets. Use GitHub Actions secrets for OAuth (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `EMAIL_TO`).

## Security & Configuration Tips
- Do not add `client_secret.json` or refresh tokens to the repo.
- Prefer `config.yaml` for runtime defaults and GitHub Actions secrets for environment-specific values.
