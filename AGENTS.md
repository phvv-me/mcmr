# My Code, My Rules

Define and enforce the engineering rules that make your code yours.

## Working Rules

- Keep the public surface small and documented.
- Prefer one boring command per task such as install, lint, typecheck, test, build, and publish.
- Update `README.md`, `SYSTEM.md`, and `CHANGELOG.md` when behavior changes.
- Do not add stack details to the README unless users need them to install or run the project.
- Do not commit, tag, publish, or push unless explicitly asked.

## Commands

- Install with `uv sync && maturin develop --release`
- Lint with `uv run ruff check . && uv run ruff format --check .`
- Typecheck with `uv run mypy src && uv run pyrefly check && env -u PYTHONPATH uv run ty check --error-on-warning`
- Test with `uv run pytest`
- Measure the mock floor with `uv run python -m mcmr.commands.cli floor --samples 9 --output .benchmarks/mock-floor.json`
- Build the core crate with `cargo build --manifest-path src/core/Cargo.toml --release`, test it
  with `cargo test --manifest-path src/core/Cargo.toml`, and lint it with
  `cargo clippy --manifest-path src/core/Cargo.toml`
- Analyze a repository with `uv run python -m mcmr.commands.cli check <path>`
- Build with `uv run python -m build --outdir .dist`
