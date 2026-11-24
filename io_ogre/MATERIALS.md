# Material mapping in the Blender 5.2 adaptation

The classic OGRE exporter reads the Principled BSDF node selected by Blender's shader wrapper. Renaming that node is supported. Arbitrary shader graphs are not baked to textures.

| Blender input | Classic OGRE output |
| --- | --- |
| Base Color | `diffuse` RGB; a directly connected image becomes a base texture unit |
| Alpha below 1, or a linked Alpha input | Alpha blending and disabled depth writes; texture alpha should come from the base image |
| Roughness and Metallic values | First two `specular` components with RTSS `lighting_stage metal_roughness` |
| One image through Separate Color: Green → Roughness, Blue → Metallic | RTSS packed metallic/roughness texture; preserve the Green/Blue channel convention |
| Image → Normal Map → Normal | RTSS normal-map reference; enable mesh tangents for tangent-space normal maps |
| Emission Color image | Additive texture unit and RTSS late additive blend |
| Use Fixed Function Pipeline Parameters | Approximate PBR values using the older diffuse/specular model |

Image textures should use UV coordinates. Complex procedural graphs, standalone metallic/roughness images in the classic path, ambient occlusion, arbitrary BSDF types, and custom engine shaders are not automatically reconstructed. RTSS must be enabled in the receiving engine. The legacy normal-map syntax is retained for compatibility with the bundled OGRE 13 tools; newer OGRE versions also support it. See the [OGRE RTSS reference](https://ogrecave.github.io/ogre/api/14/rtss.html).

Opaque materials no longer become transparent merely because Blender's deprecated material flags report a blend mode. For explicit control, add a string custom property to the material named `ogre_alpha_mode`, with value `OPAQUE`, `MASK`, or `BLEND`. `AUTO` (or no property) reads the Alpha input. For `MASK`, a float custom property `ogre_alpha_threshold` controls the cutoff from 0 to 1; its default is 0.5. Alpha-linked graphs default to blending; choose `MASK` explicitly for cutouts.

Saved, generated, and packed images can be exported with **Convert Images: None**. Generated and packed images are saved as copies without changing their original paths or packing. Optional resizing and format conversion require ImageMagick; configure its `magick.exe` or `convert` executable in add-on preferences. A missing source image produces an error explaining which image needs saving or packing. Exported texture filenames replace spaces and filename punctuation with underscores, and material references use the same names.

## Imported material scripts

Import reads basic diffuse/alpha, emission, specular/PBR values, blending and image references. Local `import ... from "file.material"`, single material inheritance, abstract material templates, `$variables`, and named technique/pass/texture-unit overrides are expanded before those basic properties are read. Keep imported scripts and textures inside the asset folder. Cycles, missing parent materials and missing imported files produce warnings. The geometry retains its material names with basic placeholders when a definition cannot be resolved.

This is a basic material translation, not an OGRE shader compiler. Only the first supported technique/pass is represented; advanced multi-pass effects, shader programs, texture aliases, complex resource-group layouts and every script-language feature are not reproduced in Blender. A child script without its parent script cannot recover the parent's texture rules. For example, the public Tires sample in issue #156 omits its referenced base script; include that script to resolve its inherited appearance.

## Runtime materials and animation blending

An OGRE mesh stores material names, rather than embedding a renderer-independent Blender shader. Name a Blender material `extern.RuntimeMaterial` to reference an engine-created material named `RuntimeMaterial`. Resource Prefix leaves these external names unchanged. Geometry without a material receives `_missing_material_`; the application may replace it after loading. See the [OGRE material reference](https://ogrecave.github.io/ogre/api/14/_material-_scripts.html).

For cumulative upper/lower-body skeletal animations, each clip must leave the other body's bones at identity or exclude their channels. Two clips with nonzero transforms on the same bones accumulate those transforms. Switching the OGRE blend mode does not isolate body parts automatically; remove the unwanted channels or key their neutral transforms.
