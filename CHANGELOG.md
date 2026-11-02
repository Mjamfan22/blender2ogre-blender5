# Blender 5.2 adaptation 0.9.8

Public fork update: connected the adaptation to OGRECave/blender2ogre's fork network, retained the existing project URL and original README/images, and updated the contribution and installation guides for public access. The release and review PR remain drafts. The installer is unchanged.

Presentation update: restored the actual original blender2ogre README sections and their images, appended our fixes separately, and removed the generated demo gallery and preview scripts. The installer is unchanged.

Repository documentation update: restored the original project description, added a consolidated fixes/improvements list, and organized development files into `tests/`, `tools/` and `docs/validation/`. Build outputs and disposable profiles now live under ignored `.build/`. The verified installer and runtime behavior are unchanged.

Prepares the existing fixes for GitHub review. Runtime import/export behavior is unchanged from 0.9.7.

- Updates the installer version and installation guide, and corrects the stale adaptation version in the third-party notice.
- Adds repository-level review documentation, patch notes, validation evidence, screenshots, source history and a draft release alongside the self-contained installer. These review assets are outside the installable add-on.
- Carries forward the faster XML and bulk mesh import, shared material resource lookup, animation fixes and protected import/export workflows from the previous releases.

All 73 regressions run against the installed 0.9.8 ZIP in isolated Blender 5.2.3. See the repository's review guide for scope, evidence and remaining limitations.

# Blender 5.2 adaptation 0.9.7

Speeds up import without reducing geometry or texture quality. The 190,826-triangle Bakugan body imported in about 8 seconds versus 39 seconds in the previous release on the test computer. Timings vary by asset and hardware.

- Replaces the mesh XML DOM reader with ElementTree and collects vertex attributes and faces directly, avoiding repeated recursive searches. Releases the XML tree before constructing the Blender mesh.
- Transfers positions, polygon indices, UV layers and vertex colors through contiguous bulk arrays using Blender's bundled NumPy.
- Builds merged static shared-geometry submeshes directly in one mesh, retaining one source vertex buffer and per-face materials. Animated meshes and separate-submesh imports retain their established behavior.
- Reuses imported materials within a single import.

Adds five import regressions. All 73 checks run from the independently installed release ZIP. The complete Bakugan comparison checks every triangle corner's positions, custom normals, all eight UV layers and material assignment against the previous release. No differences were found; the shared vertex buffer contains 121,422 vertices instead of three duplicated copies.

# Blender 5.2 adaptation 0.9.6

Fixes the missing shared materials reported while importing the Bakugan Dragonoid body from a Rigs of Rods/Sim-Monsters pack.

- Finds nearby recognized asset-pack roots and resolves shared script/texture references across pack subdirectories. Adds an optional Resource Folder import control for other layouts.
- Resolves abstract pass/technique/texture-unit inheritance, including the `pass : specular_pass` pattern, as well as quoted named overrides.
- Discovers shared material definitions referenced by mesh submeshes even when they are not declared in the mesh's local script.
- Reads the base texture from the first pass instead of replacing it with a later specular/shine map. Preserves supported inherited alpha rejection and image alpha.
- Reports ambiguous/missing resources and cyclic templates. Leaves original pack files unchanged and avoids warnings for unused material definitions.

Adds nine shared-resource regressions, including the full 190,826-triangle Bakugan body and its three image-backed materials. All 68 checks run from the independently installed release ZIP. Custom OGRE shaders and later-pass lighting/reflection effects remain approximations.

# Blender 5.2 adaptation 0.9.5

First repair batch from an audit of all 27 open OGRECave/blender2ogre issues. This is a local adaptation, not an upstream release or a claim that all upstream reports are resolved.

- Fixes selected-only export through nested hierarchies and merge collections.
- Adds Resource Prefix, Apply Modifiers and sparse node-key export controls, including consistent resource references and manual LOD naming.
- Fixes opaque material export with modern Blender transparency settings; provides explicit alpha-mode/cutoff overrides and a documented material mapping.
- Saves generated/packed textures without changing their paths or packing; improves missing image and ImageMagick diagnostics.
- Adds basic local material imports, inheritance, variables, abstract templates and named overrides, with missing-dependency/cycle warnings. Fixes packed metallic/roughness lookup when the Principled node has been renamed.
- Corrects light and camera forward directions using separate orientation attachment nodes; verifies the reporter's nested scene sample.
- Fixes imported bone directions by assigning length before the bind matrix. Converts skeletons into mesh bind space, handles rotated/scaled/offset rigs with uniform relative scale, and avoids sharing incompatible bind spaces.
- Corrects exported bone IDs when filtering deform bones, and throttles unshared-mesh progress reporting.
- Replaces the dead Meshmoon tutorial link and documents external materials, cumulative animation authoring, collider integration and Linux dependency limits.

Validation adds 22 issue/related regressions to the previous 37 checks and runs all 59 from an independently installed ZIP in Blender 5.2.3. The original animated character and nested-scene attachments are tested numerically. Character weight trimming is disabled for the deformation comparison. Disabling skeletal export no longer leaves a dangling skeleton reference. AO export, direct binary serialization, automatic compound physics shapes, full OgreNext rendering and Linux runtime verification remain open work; detailed statuses and evidence are in the development documentation.

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

Validation uses factory-startup background Blender processes with isolated profiles, real converter and upgrader binaries, generated failure fixtures, and original OGRE sample assets. It includes an independently installed copy of the final ZIP. Development evidence and test tools are optional and kept in the development folders; the installer contains runtime files, user documentation, and licenses only.

The bundled converter remains OGRE 13.3.2 for the verified classic workflow. This release does not claim verified OGRENext, custom engine shaders, or every advanced upstream exporter option. See `README.md` for installation, migration, usage, and the precise compatibility limits.
