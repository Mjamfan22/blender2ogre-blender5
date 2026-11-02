# Repository layout

| Path | Purpose |
| --- | --- |
| `io_ogre/` | Installable runtime, user documentation and bundled Windows tools |
| `tests/` | Current regression suites; `tests/fixtures/README.md` describes optional external fixtures |
| `tools/` | Packaging and verification helpers |
| `docs/validation/` | Sanitized release/test evidence and per-file hashes |
| `images/` | Original upstream screenshots and feature examples |
| `.build/` | Ignored local outputs, scratch files and disposable Blender profiles |
| `examples/`, `test/`, `feature_tests/`, `archived_code/` | Original upstream reference material |

The installed add-on needs only `io_ogre/`. Tests and tools are kept in the source repository for maintainers and CI; they are not bundled in the installer. The v0.9.8 runtime archive is unchanged by this repository-only reorganization. Its historical package documentation describes the development layout used when that ZIP was built; current source commands are in [CONTRIBUTING.md](../CONTRIBUTING.md).
