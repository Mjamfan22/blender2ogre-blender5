# Review guide

The review build is **v0.9.12**. It adds multi-file import with filename-named collections, independent failure rollback, combined reports and consistent selected-rig reuse. It also retains the placeholder filename/diagnostic fixes and explicit textures on legacy RoR assets. See [the batch import guide](BATCH_IMPORT.md). This repository also adds review documentation, original upstream images, portable checks and sanitized release evidence.

The README restores the actual upstream sections and their original images, followed by [our complete fixes and improvements](FIXES.md). Development files use the standard layout described in [LAYOUT.md](LAYOUT.md).

1. Read [the patch notes](../CHANGELOG.md) for the full progression from 0.9.4 to 0.9.12.
2. Review the draft PR comparing `main` with `upstream/master`. The latter is the exact original adaptation baseline; it is a comparison reference. Leave the PR in draft while reviewing.
3. Download the public installer ZIP from [v0.9.12](https://github.com/Mjamfan22/blender2ogre-blender5/releases/tag/v0.9.12), or choose an earlier version from [the release archive](RELEASES.md). Each release includes its own changelog and documentation bundle. Compare the installer SHA-256 with that release's checksum file; for the current version, [the runtime manifest](validation/runtime_manifest.json) records the same hash. Install the ZIP, not the repository's source archive.
4. In a disposable Blender scene, import a mesh, inspect its normals/UVs/materials, preview its animation if present, then export and re-import a copy. Save existing work before restarting Blender.
5. Read [the validation limits](VALIDATION.md), [upstream issue audit](UPSTREAM_ISSUES.md) and [remaining work](ROADMAP.md). The audit describes the 2026-10-25 snapshot, not the current issue count or upstream closure status.

The installer is self-contained. Tests, build scripts and validation records are never included in it. The repository is public and belongs to OGRECave/blender2ogre's fork network. Releases v0.9.4 through v0.9.12 are public; the review PR remains a draft for the owner's review.

## Suggested review points

- `io_ogre/import_batch.py` and `ui/importer.py`: multi-selection/drop properties, per-file collection grouping, rollback boundaries, report aggregation and original selected-rig context.
- `io_ogre/ogre/fast_xml.py` and `ogre_import.py`: XML collection, shared static geometry, bulk corner attributes and the separate rig/morph path.
- `io_ogre/ogre/resource_index.py`, `material_resolver.py`, `material_reader.py`, `material_import.py`: bounded pack discovery, inherited materials and image mapping.
- `io_ogre/animation.py`, `ogre/skeleton.py`, `ogre/scene_import.py`: Blender 5 action slots, bind-space conversions and scene hierarchy.
- `io_ogre/util.py` and staging/transaction code: conversion scratch files and failure recovery. Locate the actual implementations using search if files are reorganized later.
- `tests`: synthetic and fixture-dependent regressions; missing private fixtures are explicitly skipped in the clean-checkout subset.

Do not treat all 27 audited issues as fixed. Engine, Linux, rendering and feature dependencies are recorded explicitly. This PR does not submit work to the upstream project.
