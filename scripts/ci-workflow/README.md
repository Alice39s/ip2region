# ip2region CI workflow control plane

This package is the single source of truth for binding and maker build/test
commands used locally and by GitHub Actions.

```bash
uv sync --all-groups --locked
uv run ip2region-ci validate
uv run ip2region-ci list
uv run ip2region-ci run binding-cpp
uv run ruff check .
uv run pytest
```

Component commands are structured argument lists in `components.toml`. The
runner never invokes a shell, applies an explicit timeout to every step, and
rejects unknown manifest fields.
