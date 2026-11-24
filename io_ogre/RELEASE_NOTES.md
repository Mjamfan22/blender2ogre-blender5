# Blender 5.2 adaptation 0.9.4

This release hardens the classic OGRE workflow for Windows x64 and Blender 5.2.3 LTS. It retains the upstream blender2ogre identity, `io_ogre` module, credits, and LGPL 2.1-or-later licensing.

- Preserves enabled/disabled modifiers, rig visibility, action slots, poses, transforms, selection, and fractional timeline position after export, including failures.
- Rolls back objects and other data created by failed imports, while preserving existing materials and scene environment settings.
- Keeps import conversion away from source files. Source XML and existing companion XML are never removed by the legacy import cleanup option.
- Stages complete export output and restores previous files if publishing the completed export fails. Respects the mesh overwrite option.
- Fixes unshared export for missing materials, vertex alpha, multiple UVs, skin seams, unused material slots, and material references. Automatically retains shared geometry where needed for shape animation.
- Uses exact bind transforms for skeleton import, replacing legacy axis heuristics. Fixes local rotation/translation interpretation and scale channel signs.
- Corrects clip timing and fractional-frame sampling, includes final samples, handles shared actions with different slots, and adds linear DotScene transform animation import.
- Improves classic material color, transparency, emission, and base-texture import; protects pre-existing materials; fixes quoted texture paths and combined material references.
- Runs native tools against isolated scratch copies to support non-ASCII asset paths. Adds timeouts, relocated bundled tool recovery, configuration validation, and atomic configuration saves.
- Validates geometry references before constructing Blender mesh arrays and retains source triangle topology and custom normals.

Validation uses factory-startup background Blender processes with isolated profiles, real converter and upgrader binaries, generated failure fixtures, and original OGRE sample assets. It includes an independently installed copy of the final ZIP. Development evidence and test tools are optional and live under `ChatGPT`; the installer contains runtime files, user documentation, and licenses only.

The bundled converter remains OGRE 13.3.2 for the verified classic workflow. This release does not claim verified OGRENext, custom engine shaders, or every advanced upstream exporter option. See `README.md` for installation, migration, usage, and the precise compatibility limits.
