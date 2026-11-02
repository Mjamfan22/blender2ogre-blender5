# Known limits and remaining work

This is a verified Windows/classic-OGRE adaptation. It does not resolve every upstream issue or implement every engine feature.

| Remaining work | Current boundary |
| --- | --- |
| Linux native tools and installation | Windows executables are bundled; Linux loader dependencies and snap/flatpak paths remain unverified. |
| OGRENext rendering | Existing paths remain, but full channel conversion and an engine-rendered comparison need separately configured tools. |
| Ambient occlusion | An explicit Blender input convention, packed/separate channel behavior and renderer validation are still needed. |
| Compound collision shapes | Automatic engine-specific serialization is not implemented; see the runtime physics guide. |
| Modern OGRE material profiles | Classic syntax remains; modern renderer profiles require engine validation. |
| Direct binary serialization | Binary files still pass through a native XML converter. Import parsing is faster, but this is not a replacement binary backend. |
| Advanced materials/animation | Arbitrary shader programs, multi-pass lighting, constraints, inheritance modes and independently animated mesh/rig bind spaces retain limits. |

The [dated issue audit](UPSTREAM_ISSUES.md) links the original reports and separates tested local fixes from these dependencies. No upstream report was closed or represented as resolved by this private review.
