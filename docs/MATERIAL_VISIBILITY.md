# Banner backs and material visibility

v0.9.13 fixes gray banner backs covering sponsor artwork. The texture files were loaded correctly, but the importer previously displayed both sides when a script omitted `cull_hardware`. A reverse-facing gray fabric surface could therefore hide the artwork meant to be seen from the track.

OGRE's default is `cull_hardware clockwise`: reverse-facing triangles are culled. The importer now applies the matching Blender back-face culling setting. Explicit `cull_hardware none`, including inherited settings, retains two-sided display. This changes material visibility without changing geometry, UVs, normals, texture connections or material assignments. See [OGRE's culling documentation](https://ogrecave.github.io/ogre/api/latest/_material-_scripts.html).

The setting applies in Blender Material Preview/EEVEE, where the reported issue was verified. Arbitrary custom shaders and receiving-engine rendering remain within the existing [compatibility limits](ROADMAP.md).

## Existing imports

Upgrading the add-on does not rebuild existing materials. Re-import the affected asset with v0.9.13, or enable **Backface Culling** on materials that use OGRE's default culling. Preserve materials explicitly authored as two-sided. In the reported open scene, 18 banner materials were repaired and the sponsor artwork was visibly restored, preserving object data, assignments, transforms and selection.

An import report with no errors confirms that the data loaded successfully. It cannot by itself establish that every visual setting matches the source engine. The new regression suite includes a real EEVEE render: a reversed gray backing hides a red sponsor surface when both sides are drawn; restoring source culling reveals the sponsor surface. Default/explicit culling, inherited two-sided settings and child overrides are also covered.

See [validation](VALIDATION.md), [version notes](../CHANGELOG.md) and [release downloads](RELEASES.md).
