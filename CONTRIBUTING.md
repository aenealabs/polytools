# Contributing to polytools

Thank you for taking the time to contribute.

## Ground rules

- **Zero external dependencies.** polytools must remain pure Python stdlib. PRs that introduce any third-party import will not be merged.
- **Python 3.9+.** All code must run on Python 3.9 through the latest stable release.
- **Tests required.** Every new feature or bug fix must include a corresponding test. The CI matrix runs on 3 operating systems × 5 Python versions — please run tests locally before opening a PR.
- **Keep it focused.** polytools does one thing: schema generation. Feature requests outside that scope belong in a separate package.

## Setting up a development environment

```bash
git clone https://github.com/aenealabs/polytools
cd polytools
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -v
```

To run against a specific Python version, use `hatch`:

```bash
pip install hatch
hatch run test
```

## Adding a new type annotation

1. Add the conversion logic to `src/polytools/_schema.py`.
2. Add tests to `tests/test_schema.py` covering the new type.
3. If the new type requires special handling in the Gemini formatter, update `src/polytools/_providers/_gemini.py` and add a Gemini-specific test in `tests/test_providers.py`.

## Adding a new provider

1. Create `src/polytools/_providers/_<provider>.py` following the pattern of the existing formatters. It must accept a `FunctionMeta` and return a `dict`.
2. Add `to_<provider>()` to the `Tool` class in `src/polytools/_decorator.py`.
3. Include the new provider in `Tool.to_all()`.
4. Add a test class in `tests/test_providers.py`.
5. Document the output format in `README.md`.

## Submitting a pull request

1. Fork the repository and create a branch: `git checkout -b fix/my-fix` or `feat/my-feature`.
2. Make your changes and add tests.
3. Run `pytest tests/ -v` — all 91+ tests must pass.
4. Open a pull request against `main` with a clear description of what changed and why.

## Reporting bugs

Open an issue using the **Bug report** template. Include the Python version, OS, the function you decorated, and the full traceback.

## Suggesting features

Open an issue using the **Feature request** template. Explain the use case, not just the solution.

## Code style

polytools uses no formatter or linter by choice to keep contributor setup minimal. Please follow the style of the surrounding code: 4-space indentation, descriptive variable names, module-level docstrings on every file.
