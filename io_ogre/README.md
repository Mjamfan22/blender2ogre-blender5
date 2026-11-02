# blender2ogre — Blender 5.2 adaptation

Version 0.9.8, for Windows x64 and Blender 5.2.3 LTS.

This is a local compatibility adaptation of [OGRECave/blender2ogre](https://github.com/OGRECave/blender2ogre), retaining its `io_ogre` module name, upstream authors, and LGPL license. It is not an official upstream release.

## Install

1. In Blender, open **Edit → Preferences → Add-ons**.
2. Use the menu at the upper right and choose **Install from Disk**.
3. Select `blender2ogre_Blender_5_2_v0.9.8.zip` and enable **OGRE Importer-Exporter (.scene, .mesh, .skeleton)**.

The ZIP contains one `io_ogre` folder. Install it as a legacy add-on; do not select the entire project folder. Disable the older `io_ogre` add-on before installing the replacement, then restart Blender and enable the new version. Keep one active `io_ogre` installation.

The bundled Windows OGRE converter and mesh upgrader are selected automatically. Missing paths to a previous bundled/default converter are repaired when the new package loads; custom tool choices remain available in **OGRETOOLS_XML_CONVERTER** and **OGRETOOLS_MESH_UPGRADER**. The executables and DLLs are inside `io_ogre/tools/windows`.

The clean source and installer are self-contained. `ChatGPT` contains optional development files and can be deleted. Neither the old Blender 4 tool library nor any development scripts are required at runtime.

## Use

- **File → Import → Ogre3D (.scene and .mesh)** reads binary `.mesh`, mesh `.xml` (normally `.mesh.xml`), and `.scene` files. Linked `.skeleton` files supply bones and animation clips; standalone skeleton import is not provided. Keep linked meshes, skeletons, material scripts, and textures together. Drag and drop is also available.
- Shared material scripts and textures in nearby recognized resource packs are found automatically, including the `parts` and `parts/shared` layout in Rigs of Rods truck packs. For another layout, set **Resource Folder** in the import dialog (`IM_IMPORT_RESOURCE_PATH` in scripts). Leave it blank for automatic detection. Import preserves the pack files. After upgrading, re-import the mesh to rebuild materials that previously used placeholders.
- Import uses faster XML reading and bulk mesh-data transfers automatically. With **Merge Submeshes** enabled, static submeshes that use shared geometry reuse one vertex buffer. This reduces duplicate vertices while preserving triangle corners, UV layers, normals and material assignments. Rigged and shape-animated meshes retain their existing topology path. Import speed varies with the asset and computer; binary meshes still pass through the native XML converter.
- **File → Export → Ogre3D (.scene and .mesh)** exports selected objects to a `.scene` file with binary `.mesh`, linked `.skeleton`, material scripts, and supported textures. Select a mesh and keep an active object before exporting.
- Work in Object Mode for import/export. Put skeletal and shape animation actions into NLA strips to export named clips. Multiple clips use their individual Blender 5 action slots. Node transform animation also exports a single active action without an NLA strip. Imported clips are stored in muted NLA tracks; activate the desired track or action to preview it.
- Import conversion uses disposable scratch files and preserves the input files and any existing companion XML. The old import XML cleanup option is retained for script compatibility and never deletes source XML. The export **Clean up XML files** option controls whether generated mesh/skeleton XML is included beside the binary output.
- Export stages its output before replacing destination files. A failed operation restores editing state and leaves existing export files intact. A failed import removes the data it created. Material imports create new materials instead of rewriting existing materials with matching names.
- The default OGRE coordinate convention is Y-up (`xz-y` on export). Import assumes that convention. Scene transforms are preserved through parent objects. Lights use the exporter's established factor-of-ten energy conversion.
- **Selected Only** retains necessary ancestor transforms while excluding their unselected meshes, lights, cameras and siblings, including unselected members of merge collections. **Resource Prefix** prefixes exported object/resource names without renaming source datablocks; `extern.` materials keep their engine names. The scripting property is `EX_EXPORT_PREFIX`.
- **Apply Modifiers** (`EX_APPLY_MODIFIERS`) controls evaluated geometry; it leaves source modifiers unchanged. **Only Write Node Keyframes** (`EX_NODE_KEYFRAMES`) exports authored key times and clip endpoints. Leave sparse sampling off for constraints, drivers, Bezier interpolation and procedural motion; the default samples every frame.
- Meshes and rigs may have different translation, rotation and uniform positive scale at bind time. Skeletons are converted into mesh space. Shared Armature falls back to a separate skeleton when bind spaces differ; nonuniform/sheared relative bind transforms are rejected. Skeletal clips start at frame 0 on import. Weight trimming intentionally removes small influences; use a zero threshold when comparing exact deformation. Check receiving-engine limits on influences per vertex.
- Use **Write Log file** when diagnosing material references or converter failures. The operation report lists missing dependencies or unsupported data. Invalid or unsuccessful operations return a cancelled result. Native conversion processes have a 120-second timeout.

## Compatibility and limits

This package targets the classic OGRE mesh workflow using bundled **OGRE 13.3.2 OgreXMLConverter**. The OGRENext path from upstream is retained, but OGRENext/V2 binary conversion needs a separately configured `OgreMeshTool` and has not been verified here. Optional image format conversion still requires ImageMagick. Neither optional program is included.

The release checks cover mesh geometry, multiple UV maps, custom normals, POINT/CORNER color attributes and alpha, classic materials and textures, skeleton and shape clips, linear DotScene transform animation import/export, nested scenes, cameras, lights, LOD generation, and edge lists. Original OGRE robot and Ogre head samples are included in the test coverage. The animated robot is checked numerically after export and re-import, rather than checking only clip names.

Skeleton import uses OGRE bind matrices directly, including animated translation and rotation in each bone's own frame. Bone display axes may differ from the older heuristic importer. Nonuniform relative bind scaling, unusual inheritance modes, independently animated mesh/rig object transforms, constraints, shader programs, particle systems, skybox baking, and engine-specific material techniques retain limitations and are not promised to be lossless. Node animation import reads linear transform tracks; spline curves and camera-property animation are not reconstructed.

Classic material import handles diffuse color/alpha, emission, a base texture including quoted filenames, alpha blending, and supported metallic/roughness values. Basic local imports, material inheritance, variables and named overrides are supported; missing dependencies and cycles are reported. Complex multi-pass and custom shader materials still require engine-specific work. Geometry without materials receives the upstream `_missing_material_` placeholder. See [MATERIALS.md](MATERIALS.md) for the mapping and [Physics.md](Physics.md) for collider authoring/runtime integration.

Unshared geometry now preserves alpha, multiple UVs, material names, and skin seams. When a shape-animated mesh requests unshared geometry, the exporter automatically uses shared geometry and reports the fallback so morph data is retained. Newer native mesh processing options that the bundled OGRE version cannot perform produce explicit warnings. OGRENext and optional external tools remain outside the verified classic OGRE release scope.

No `.ogre` file was found in the inspected local reference libraries. This package does not invent support for that extension. Supply an actual file if a separate `.ogre` format needs investigation.

The bundled tools are Windows executables. Linux requires native OGRE tools and their shared-library dependencies; pointing at an executable alone cannot resolve a missing `libOgreMain.so`. Linux/snap/flatpak installation and library-loader behavior are not verified by this Windows release. Use the ZIP installer in a writable user profile instead of copying into a read-only system add-ons directory.

## Changes and attribution

The baseline is upstream commit `0d094a40a589752802a9f8823cf08cd8acd6f8fe` (2026-03-15), compared with the user's original `blender2ogre` archives. Local changes add Blender 5 action-slot access, per-clip sampling, matrix-based skeleton import, color/UV fixes, hierarchical scene and node animation import, camera projection round trips, material translation, protected conversion scratch files, staged output, rollback and editing-state restoration, converter path repair/timeouts, and paired RNA registration/cleanup. Local adaptation files and modified upstream files remain under LGPL 2.1 or later. See `RELEASE_NOTES.md` for the release summary.

See `LICENSE.txt`, `THIRD_PARTY_NOTICES.txt`, `UPSTREAM_README.md`, and `CHANGELOG.txt` for original licensing, authors, and upstream guidance. Upstream tutorial image links in `UPSTREAM_README.md` refer to the upstream repository; they are not required for installation.
