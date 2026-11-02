# Fixes and improvements in this adaptation

Changes relative to upstream baseline `0d094a40a589752802a9f8823cf08cd8acd6f8fe`, delivered across versions 0.9.4–0.9.8. This list describes completed local changes; it does not claim every upstream report is resolved. See [the issue audit](UPSTREAM_ISSUES.md) for individual reports and [the changelog](../CHANGELOG.md) for release history.

## Blender 5 compatibility and installation

- Added Blender 5 action-slot access for sampling, assigning and restoring animation actions, including multiple named NLA clips.
- Paired RNA/property registration with cleanup and tested repeated registration cycles.
- Initialized converter/operator fields before use and provided an installable, single-module legacy add-on ZIP.
- Bundled the compatible Windows converter, upgrader and DLLs with source/license notices; repaired missing old bundled/default paths while preserving custom tool choices.
- Added configuration validation, atomic saves, native-process timeouts and actionable optional-tool diagnostics.

## Import speed and geometry

- Replaced mesh XML DOM construction and repeated recursive searches with ElementTree and direct numeric collection; released the tree before allocating Blender mesh arrays.
- Transferred positions, polygon/loop indices, all UV layers and vertex colors using contiguous bulk arrays and Blender's bundled NumPy.
- Built compatible merged static shared-geometry submeshes directly in one mesh, preserving per-face materials and avoiding duplicate buffers and an object join.
- Reused imported materials by source name within each import. Rigged, morph-animated and separate-submesh imports retain their established topology path.
- Validated declared buffer counts, face indices and attribute lengths before mesh construction, including separate vertex buffers.
- Preserved source triangles, custom normals, UV seams, POINT/CORNER vertex colors and alpha; corrected unshared export, missing/unused material slots and material/submesh names.
- Kept skin seams and corrected filtered bone IDs for shared and unshared geometry.
- Used shared geometry with a report when unshared export would lose shape-animation data.
- Throttled unshared-mesh progress reporting to avoid excessive console updates.

The measured 190,826-triangle import improved from 39.019 to 7.706 seconds in the documented fresh-process comparison. All eight UV layers, custom normals and material assignments matched at every triangle corner. The 121,422 source vertices replace three duplicated buffers, with no triangle decimation or welding of distinct source vertices. [Measurement conditions](VALIDATION.md).

## Materials and images

- Found recognized nearby asset-pack roots and shared script/texture subdirectories, with an optional Resource Folder control for other layouts.
- Found material definitions referenced by submeshes even when absent from the mesh's local script.
- Resolved local/shared imports, inheritance, scoped variables, abstract material/pass/technique/texture-unit templates and quoted named overrides.
- Reported missing/ambiguous dependencies and inheritance/template cycles without warning about unused definitions.
- Read the base texture from the first pass rather than overwriting it with a later specular/shine map.
- Mapped supported diffuse color/alpha, emission and base textures, including quoted filenames.
- Corrected opaque, blended and explicitly masked material export using modern Blender settings and documented alpha-mode/cutoff overrides.
- Preserved supported inherited alpha rejection and image alpha.
- Fixed packed metallic/roughness lookup when the Principled node is renamed, and improved missing ImageMagick messages.
- Saved generated/packed texture copies without changing their source paths or packing.
- Created new imported materials rather than rewriting pre-existing same-named materials; retained material references/placeholders when definitions are unavailable.

## Skeletons, animation and scenes

- Used OGRE bind matrices directly and corrected local bone rotation, translation and scale interpretation.
- Set edit-bone length before its bind matrix to avoid losing orientation on zero-length bones.
- Converted skeletons into mesh bind space, including differing translation, rotation and uniform positive scale; rejected unsupported nonuniform/sheared relative bind transforms explicitly.
- Used separate skeletons when shared armatures have incompatible bind spaces and avoided accidental reuse of an existing same-named rig.
- Preserved named skeletal and shape clips, per-clip sampling and action slots; corrected fractional timing, final samples and imported clip starts.
- Added hierarchical scene and linear node-transform animation import, including nested transforms and camera projection round trips.
- Corrected light/camera forward directions with separate orientation attachments that leave children correctly placed.
- Removed dangling skeleton references when skeletal export is disabled.
- Added optional authored-node-key sampling with fractional clip endpoints while retaining baked sampling by default.

## Export controls and file/state protection

- Fixed Selected Only across nested hierarchies and merge collections, retaining needed ancestor transforms without exporting unselected object payloads.
- Added Resource Prefix consistently across exported object/resource references and manual LOD names; preserved source names and external material names.
- Added Apply Modifiers without changing source modifier settings.
- Used scratch copies for native conversion, supporting non-ASCII/spaced paths and preserving input meshes and pre-existing companion XML.
- Prevented the legacy import XML cleanup option from deleting source XML.
- Staged complete export output before replacing destination files; restored previous output after a publish failure and respected overwrite controls.
- Rolled back data created by a failed import while retaining pre-existing materials and scene environment settings.
- Restored selection, active object, modifier/rig visibility, actions/slots, transforms and fractional timeline position after exports, including failure paths.

## Documentation, packaging and checks

- Added current installation/upgrade instructions, material mapping and animation-authoring guidance; replaced the dead Meshmoon tutorial link and documented physics/Linux/OGRENext limits.
- Retained the upstream project identity, full Git ancestry, author credits and LGPL licensing, along with unmodified tool binaries and their notices.
- Added actual ZIP-install tests and numeric geometry/deformation comparisons.
- Verified all 73 release checks in Blender 5.2.3 and provided a 65-check self-contained subset with explicit fixture skips.
- Added CI for syntax, exact runtime hashes, deterministic package bytes and documentation links; made archive ordering consistent between Windows and Linux.
- Organized development files into `tests/`, `tools/` and `docs/validation/`; local outputs and profiles are ignored under `.build/`.

AO export, a direct binary backend, automatic compound collider serialization, Linux runtime verification and complete OGRENext/custom-shader rendering remain separate work. [Known limits](ROADMAP.md).
