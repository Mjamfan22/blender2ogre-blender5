# Contributing and local checks

This private repository is for the owner's review. Preserve the upstream identity, copyright and LGPL licensing. Keep runtime behavior changes separate from documentation-only changes, and describe the trigger, resulting behavior and relevant validation in PRs.

Upstream example/legacy test folders and older root topic documents are retained as reference material. The commands below and the current guides under `docs` describe this adaptation's verification.

## Source/package checks

Use Python 3.11 or later from the repository root:

```console
python ChatGPT/tools/repository_checks.py
```

This validates Python syntax, exact runtime hashes, deterministic installer bytes and links in the review documentation. It creates a candidate ZIP under `ChatGPT/temp`; no Blender installation is needed for these static checks. After an intentional runtime change, update its version, rerun the relevant Blender regressions and regenerate the manifest/evidence before treating it as a verified release.

## Blender regressions

On Windows x64 with Blender 5.2.3 LTS installed:

```console
python ChatGPT/tools/run_checks.py --blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
```

The runner builds the deterministic ZIP, installs it using Blender's real legacy add-on installer in a disposable profile, and runs the **65 synthetic checks**. It does not use the live Blender's preferences or scene. Results are written under `ChatGPT/outputs`; eight fixture-dependent checks are explicitly skipped.

For the complete suite, supply the non-redistributed fixtures described in `ChatGPT/fixtures/README.md`, then add `--full`. That run includes the real-asset benchmark and baseline comparison. A missing fixture in full mode is an error. The fixture files and comparison snapshots stay ignored by Git.

Source-only runs, static CI and synthetic subsets must not be described as the complete installed-payload release verification. The included sanitized evidence records the actual 73-check release run separately.

Use factory-startup background Blender processes and scratch exports. Preserve source .mesh/.xml files, existing textures/materials and live editing state. Test rollback and round-trip correctness when changes affect those paths. Do not upload local model packs, caches, profiles, credentials or machine-specific logs.
