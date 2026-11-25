# Import several assets together

Requires v0.9.12 or later. Use **File → Import → Ogre3D (.scene and .mesh)**, open the asset folder, select several supported files with Ctrl/Shift, then click **Import Ogre**. You can also drag several files into Blender's 3D View while in Object Mode.

Select `.mesh`, `.mesh.xml` or `.scene` inputs. Keep skeletons, material scripts, textures and the rest of the pack in their original folders: dependencies are resolved from each asset automatically. For shared resources outside a recognized pack layout, set **Resource Folder** once for the batch. Selecting both a mesh and a scene that references it intentionally imports two separate assets; selecting both binary and XML versions also imports each selected representation.

## Collections and selection

**Collection per Asset** is enabled by default for both single and batch imports. Each file creates its own collection, for example `body.v2.mesh.xml` → `body.v2`. Existing collections and objects are kept; repeated names get Blender's normal suffixes. Mesh names still follow the established material/filename rules inside their collection.

Meshes, newly imported rigs, cameras, lights and node parents stay inside their asset's collection. Scenes retain their internal collection structure and object parenting. Transform, UV, normal, material, skinning and animation behavior is unchanged. Turn **Collection per Asset** off to retain the previous mesh/scene collection behavior.

All successfully imported objects are selected when the batch finishes. **Use selected skeleton** uses the armature active before the operation for each standalone mesh, leaving that existing rig in its original collection. Scene entities continue resolving their own linked skeletons. Use Undo once to remove the batch's scene changes.

## Reports and failed files

The combined report counts successful imports and names failed files. Each file has its own rollback boundary: a failure removes that file's newly created data and restores the previous environment/selection state, while keeping earlier successful imports and continuing to later files. Failed geometry is excluded from the totals. A partly successful batch finishes with a warning; if every file fails, the operator returns cancelled.

Batch import runs files sequentially with one set of import settings. Large files still require their usual conversion and geometry-loading time. A scene's environment and imported animation frame rate remain scene-level settings; successful files apply them in selection-list order. Existing source files are preserved. Import logs remain optional and use `blender2ogre.log` in the first input folder.

## Scripts

Existing `filepath=...` scripts remain supported. Batch scripts can use the file-browser properties:

```python
import bpy

bpy.ops.ogre.import_mesh(
    directory="D:/Assets/Truck/",
    files=[{"name": "body.mesh"}, {"name": "wheels.mesh"}],
    IM_IMPORT_INTO_COLLECTION=True,
    IM_USE_SELECTED_SKELETON=False,
)
```

When invoked through the file-browser UI, the generated Blender text script records the complete batch. Spaces, apostrophes, Unicode names and dotted basenames are quoted safely. An identical path listed more than once is imported once.

See [installation](INSTALLATION.md), [release history](RELEASES.md) and [validation](VALIDATION.md).
