# Contributing

Keep changes focused.

```sh
uv sync
maturin develop --release
uv run ruff check . && uv run ruff format --check .
uv run mypy src && uv run pyrefly check && env -u PYTHONPATH uv run ty check --error-on-warning
uv run pytest
uv run python -m build --outdir .dist
```

`uv sync` installs every tool the gate above runs, from the `dev` dependency group. `cargo test`
and `cargo clippy --manifest-path src/core/Cargo.toml` cover the Rust core the same way CI does.

Update `README.md`, `SYSTEM.md`, and `CHANGELOG.md` when behavior changes.
