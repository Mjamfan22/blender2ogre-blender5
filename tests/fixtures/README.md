# Optional fixture provenance

The default regression runner generates its fixtures and runs 65 checks. Eight additional release checks use the following locally held assets; they are not redistributed in this repository.

| Fixture | Location for full-mode reproduction |
| --- | --- |
| OGRE robot.mesh, robot.skeleton, ogrehead.mesh | `tests/fixtures/ogre_samples/` (from the OGRE sample distribution; keep its original licensing) |
| Issue #142 untitled.blend | `tests/fixtures/reporters/142/untitled.blend` |
| Issue #240 swaptest.blend | `tests/fixtures/reporters/240/swaptest.blend` |
| Private Bakugan pack | `tests/fixtures/bakugan_pack/`, preserving crd_trucks/parts layout and sources.json |
| Previous-release corner snapshots | `.build/outputs/import_benchmark_baseline.npz` and its matching baseline JSON; privately regenerate using v0.9.6, not the current version |

Reporter #142 archive: https://github.com/OGRECave/blender2ogre/files/8840314/untitled.zip · SHA-256 `8aac04994358f8ac3fc9c0676ba996307809d7e1dd404cfb8306ed376c2353c9`.

Reporter #240 archive: https://github.com/OGRECave/blender2ogre/files/15096002/swaptest.zip · SHA-256 `2f13b217a72ad26d4b03ddeb3d97ca3575d31f30abd43f4956a5cce4a0fd8117`.

No fixture is downloaded automatically. Use assets only when you have access/permission. The private pack's sources.json records the original absolute paths and SHA-256 of files copied into the local fixture. The full material check verifies the originals were unchanged. Keep this machine-specific manifest local and ignored by Git.

The full runner measures the current installed ZIP against the preserved previous-release snapshot. The baseline JSON/NPZ must describe the same fixture and must not be overwritten with a current-release import. The checked-in baseline JSON is a sanitized evidence copy, not a substitute for the private corner snapshot.
