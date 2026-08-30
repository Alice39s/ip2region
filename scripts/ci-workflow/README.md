# ip2region CI workflow control plane

This package is the single source of truth for binding and maker build/test
commands used locally and by GitHub Actions.

```bash
uv sync --all-groups --locked
uv run ip2region-ci validate
uv run ip2region-ci list
uv run ip2region-ci run binding-cpp
uv run ip2region-ci install-cangjie /tmp/cangjie-sdk
uv run ruff check .
uv run pytest
```

Component commands are structured argument lists in `components.toml`. The
runner never invokes a shell, applies an explicit timeout to every step, and
rejects unknown manifest fields.

The Cangjie installer pins the official Linux x64 SDK URL, byte length, and
SHA-256 digest. It extracts into a temporary directory with Python's safe tar
filter and only publishes a complete installation.

GitHub Actions delegates to the same manifest:

- `cpp.yml` covers native Linux, macOS, and Windows runners on x64 and ARM64.
- `bindings.yml` covers every other runnable language binding.
- `makers.yml` covers every runnable maker. The C++ maker is exercised by the
  C++ binding adapter; aliases and the unimplemented C maker remain explicit in
  the manifest.
