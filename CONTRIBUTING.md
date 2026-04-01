# Contributing

Thanks for contributing to `serp-filter-skill`.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
```

If you need local provider credentials or private spreadsheets, put them in `private/`. That directory is intentionally ignored by git.

## Running Tests

```bash
PYTHONPATH=src python -m pytest -q
```

To run a smaller scope while iterating:

```bash
PYTHONPATH=src python -m pytest tests/test_cli.py -q
```

## Project Structure

- `src/serp_filter/` contains the CLI and filtering pipeline.
- `tests/` contains the regression suite.
- `config/` contains safe example config templates.
- `examples/` contains public sample inputs used by the README.

## Pull Requests

- Keep pull requests focused on one change.
- Update tests when behavior changes.
- Update `README.md` or `CHANGELOG.md` when the public workflow changes.
- Do not commit credentials, local blocklists, or generated output files.
