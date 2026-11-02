# Install and upgrade

Verified platform: **Windows x64, Blender 5.2.3 LTS**, classic OGRE workflow. The installer bundles the Windows OGRE 13.3.2 converter/upgrader and their required DLLs. See [licenses](../NOTICE.md).

1. Download `blender2ogre_Blender_5_2_v0.9.8.zip` from the private draft release. Check its SHA-256 against `SHA256SUMS.txt` or [the runtime manifest](../docs/validation/runtime_manifest.json).
2. Save open work. In **Edit → Preferences → Add-ons**, disable any older `io_ogre` copy. Keep one installation of this module.
3. Choose **Install from Disk**, select the ZIP, and enable **OGRE Importer-Exporter (.scene, .mesh, .skeleton)**.
4. Fully close and reopen Blender. Confirm the add-on shows **0.9.8**, then use **File → Import → Ogre3D (.scene and .mesh)** or the matching Export entry.
5. Re-import meshes whose materials were created by an older version. Already-created scene objects/materials do not rebuild automatically after an add-on upgrade.

Keep linked meshes, skeletons, material scripts and textures in their original pack layout. Recognized nearby resource packs are searched automatically. For a different layout, set **Resource Folder** in the import dialog to the pack root; do not flatten or relocate the original files. With **Merge Submeshes** enabled, compatible static submeshes share one source vertex buffer for the best import performance.

Missing default/bundled converter paths are repaired when the add-on loads. A custom tool choice remains configurable in add-on preferences. Binary import/export uses native tools; a configured OGRENext path needs a separate compatible `OgreMeshTool` and is not covered by this release's verification.

If the old warning text or duplicate vertex counts persist, first confirm the loaded add-on version and restart Blender. A mesh imported before the restart still contains its old data. For further reports, use the private bug-report template with Blender/add-on versions and a minimal reproducible sample you may share.

For settings, supported material translation and animation authoring, see [the runtime guide](../io_ogre/README.md), [material guide](../io_ogre/MATERIALS.md) and [known limits](ROADMAP.md).
