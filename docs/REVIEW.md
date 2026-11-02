# Review guide

The review build is **v0.9.8**. Compared with v0.9.7, its runtime behavior is unchanged: only version/installation documentation and a stale third-party notice were corrected. This repository also adds review documentation, images, portable checks and sanitized release evidence.

The README restores the actual upstream sections and their original images, followed by [our complete fixes and improvements](FIXES.md). Development files use the standard layout described in [LAYOUT.md](LAYOUT.md).

1. Read [the patch notes](../CHANGELOG.md) for the full progression from 0.9.4 to 0.9.8.
2. Review the draft PR comparing `main` with `upstream/master`. The latter is the exact original adaptation baseline; it is a comparison reference. Leave the PR in draft while reviewing.
3. Download the draft release ZIP and compare its SHA-256 with [the validation record](../docs/validation/runtime_manifest.json). Install the ZIP, not the repository's source archive.
4. In a disposable Blender scene, import a mesh, inspect its normals/UVs/materials, preview its animation if present, then export and re-import a copy. Save existing work before restarting Blender.
5. Read [the validation limits](VALIDATION.md), [upstream issue audit](UPSTREAM_ISSUES.md) and [remaining work](ROADMAP.md). The audit describes the 2026-10-25 snapshot, not the current issue count or upstream closure status.

The installer is self-contained. Tests, build scripts and validation records are never included in it. The original libraries and the user's installed add-on were not changed for this GitHub preparation. The repository and release remain private; the release and PR remain drafts for the owner's review.

## Suggested review points

- `io_ogre/ogre/fast_xml.py` and `ogre_import.py`: XML collection, shared static geometry, bulk corner attributes and the separate rig/morph path.
- `io_ogre/ogre/resource_index.py`, `material_resolver.py`, `material_reader.py`, `material_import.py`: bounded pack discovery, inherited materials and image mapping.
- `io_ogre/animation.py`, `ogre/skeleton.py`, `ogre/scene_import.py`: Blender 5 action slots, bind-space conversions and scene hierarchy.
- `io_ogre/util.py` and staging/transaction code: conversion scratch files and failure recovery. Locate the actual implementations using search if files are reorganized later.
- `tests`: synthetic and fixture-dependent regressions; missing private fixtures are explicitly skipped in the clean-checkout subset.

Do not treat all 27 audited issues as fixed. Engine, Linux, rendering and feature dependencies are recorded explicitly. This PR does not submit work to the upstream project.
