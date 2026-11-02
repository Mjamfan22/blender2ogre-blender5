# Upstream issue audit and first repair batch

Historical audit from 2026-10-25/26, included for the 2026-11-02 private review. References to unchanged GitHub state below describe that original audit; this private repository now contains the adaptation. No upstream repository state was changed.

Update 2026-10-26: v0.9.6 extends issue #156 coverage to the user's complete Bakugan resource-pack layout, including abstract pass templates and shared global material/texture lookup. See [material resource guide](../io_ogre/MATERIALS.md). That installer had 68 checks; v0.9.8 has 73, including five performance checks. The table below records the original v0.9.5 audit unless this update says otherwise.

Repository: [OGRECave/blender2ogre](https://github.com/OGRECave/blender2ogre).
Snapshot: 2026-10-25, all 27 open issues, with all available discussion comments.
The issue endpoint also returned PR #258; it is excluded from the issue count.
Upstream master remains `0d094a40a589752802a9f8823cf08cd8acd6f8fe` (2026-03-15).
The original discussion snapshot is retained locally; this review repository includes the status summary and test results.
Reporter fixture source URLs and hashes are recorded in `tests/fixtures/README.md`; the files are not redistributed here.

These are local adaptation results. No upstream issue was closed, comment posted, pull request created or GitHub repository changed. Verified means tested in Windows x64 / Blender 5.2.3 with the bundled classic OGRE tools; it does not establish behavior in an arbitrary game engine or Linux distribution.

| Issue | Result in 0.9.5 / remaining work |
| --- | --- |
| [#273 Unshared vertices](https://github.com/OGRECave/blender2ogre/issues/273) | Verified unshared skinned geometry and binary output. Fixed filtered bone IDs for shared and unshared geometry. Emergency 5 behavior still requires that engine. |
| [#272 Missing converter attribute](https://github.com/OGRECave/blender2ogre/issues/272) | Screenshot identifies an uninitialized operator converter field. Explicit Blender operator initialization was already fixed; binary import regression added. |
| [#267 Convex colliders](https://github.com/OGRECave/blender2ogre/issues/267) | Clarified authoring/runtime responsibilities in Physics.md. Automatic Bullet compound-shape serialization remains a feature request. |
| [#266 One animation action](https://github.com/OGRECave/blender2ogre/issues/266) | Verified multiple slotted NLA skeletal clips and slot restoration. |
| [#264 Broken Meshmoon link](https://github.com/OGRECave/blender2ogre/issues/264) | Removed obsolete tutorial link from the shipped historical README; current installation guide is self-contained. |
| [#263 Resource prefix](https://github.com/OGRECave/blender2ogre/issues/263) | Added Resource Prefix UI/API option, consistent mesh/skeleton/material references, external-material exclusion, source-name preservation and manual LOD coverage. |
| [#262 Linux tool discovery](https://github.com/OGRECave/blender2ogre/issues/262) | Log shows a missing `libOgreMain.so.1.11.6` runtime dependency. Windows bundling/path repair is verified; Linux loader paths and UNIX defaults remain unverified here. Documented the difference between the executable path and its shared libraries. |
| [#255 Opaque cube appears wrong](https://github.com/OGRECave/blender2ogre/issues/255) | Fixed deprecated blend/backface-property dependence. Verified opaque, blended and explicit mask materials. |
| [#248 Selected Only](https://github.com/OGRECave/blender2ogre/issues/248) | Fixed recursive inclusion of unselected children/siblings and merge collection members. Ancestors remain as transform nodes, without their mesh/camera/light payload. |
| [#240 Scene axis swapping](https://github.com/OGRECave/blender2ogre/issues/240) | Verified the reporter's nested swaptest.blend geometry round trip; camera/light forward axes now use a separate orientation attachment that leaves children correctly placed. |
| [#231 Light direction](https://github.com/OGRECave/blender2ogre/issues/231) | Fixed and numerically checked nested light/camera world directions. |
| [#213 Material mapping docs](https://github.com/OGRECave/blender2ogre/issues/213) | Added MATERIALS.md with supported input mapping, alpha overrides, external materials and precise limits. |
| [#202 OGRE 1.14 normal maps](https://github.com/OGRECave/blender2ogre/issues/202) | Upstream maintainer confirms legacy syntax remains supported. Retained compatibility syntax and documented tangents/RTSS; no OGRE 14 renderer available for a visual comparison. Modern syntax profile remains unimplemented. |
| [#201 Ambient occlusion](https://github.com/OGRECave/blender2ogre/issues/201) | Open enhancement. Requires a defined Blender input convention, packed/separate-channel handling and engine rendering verification; not silently mapped to base color. |
| [#194 Add-on registration/install](https://github.com/OGRECave/blender2ogre/issues/194) | Clean single-module ZIP, actual isolated installation, registration cycles and bundled converters cover this package's workflow. Existing duplicate/misnamed external installations need removal as documented. |
| [#190 Skip XML / export speed](https://github.com/OGRECave/blender2ogre/issues/190) | Throttled unshared-geometry progress to roughly 100 updates and corrected progress units. Direct binary writing remains an architectural enhancement requiring a supported binary serializer; no replacement serializer was invented. |
| [#184 OgreNext DamagedHelmet](https://github.com/OGRECave/blender2ogre/issues/184) | Removed deprecated alpha access in JSON generation and added an actionable missing-ImageMagick error. Full OgreNext rendering/channel conversion remains unverified and open. |
| [#180 Import axis option](https://github.com/OGRECave/blender2ogre/issues/180) | Import uses the documented fixed OGRE Y-up convention. The ineffective old axis selector was removed in 0.9.4. Arbitrary import conventions remain unsupported. |
| [#169 Ubuntu install](https://github.com/OGRECave/blender2ogre/issues/169) | Installable ZIP avoids copying into a read-only system add-ons directory. Windows user-profile installation is verified; Ubuntu/snap/flatpak and Linux native tools remain untested. |
| [#156 Inherited materials](https://github.com/OGRECave/blender2ogre/issues/156) | Added local imports, basic inheritance, variables, abstract bases and named overrides, with cycle/missing-dependency warnings. Synthetic inheritance fixtures pass. The reporter's Tires archive lacks its base script; custom shaders and complete OGRE compiler semantics remain outside scope. |
| [#149 Cumulative animation](https://github.com/OGRECave/blender2ogre/issues/149) | Upstream discussion identifies overlapping/non-neutral authored bone channels. Added authoring guidance to MATERIALS.md; no destructive removal of source channels. |
| [#145 Texture copy failure](https://github.com/OGRECave/blender2ogre/issues/145) | Fixed generated/packed image copies and missing source diagnostics; verified conversion=None without modifying image paths/packing. |
| [#142 Twisted skeleton](https://github.com/OGRECave/blender2ogre/issues/142) | Fixed zero-length EditBone orientation loss and mesh/rig bind-space conversion. Reporter character fixture passes animated binary round trip with trimming=0. Shared armatures fall back to per-mesh skeletons where bind spaces differ. Nonuniform/sheared relative bind spaces explicitly fail. |
| [#138 Metallic/roughness maps](https://github.com/OGRECave/blender2ogre/issues/138) | Existing packed Green/Blue path retained; fixed lookup of renamed Principled nodes. Verified packed texture output/copy. Arbitrary independent maps and procedural graph baking remain unsupported. |
| [#87 Only node keys](https://github.com/OGRECave/blender2ogre/issues/87) | Added opt-in sparse sampling of authored keys plus fractional clip endpoints, with the baked default retained and interpolation/constraint limitations explained. |
| [#59 Apply modifiers](https://github.com/OGRECave/blender2ogre/issues/59) | Added Apply Modifiers switch; verified evaluated mirror geometry and unchanged source modifiers. |
| [#15 Mesh without material](https://github.com/OGRECave/blender2ogre/issues/15) | Documented the placeholder and extern.RuntimeMaterial route confirmed in upstream discussion. OGRE requires a valid material reference at load time. |

## Validation and remaining queue

The final installer is exercised by the 13 baseline checks, 24 previous release regressions and 22 issue/related regressions. The related regression catches dangling skeleton links when skeletal export is disabled. See VERIFIED_RELEASE.json for the installed module path, exact ZIP hash and final test count; source-only test runs are not release evidence.

The character sample is compared against original evaluated world-space geometry at two poses. Weight trimming is disabled to distinguish coordinate correctness from intentional loss of small influences. Native OGRE rendering may impose additional influence limits. The nested scene sample is compared numerically after export and re-import, and synthetic tests independently check the light/camera directions.

Next work with meaningful external dependencies: Linux loader validation (#262/#169), OgreNext rendered comparison (#184), AO input/export/render design (#201), compound collider runtime integration (#267), modern OGRE 14 material output validation (#202), and a supported native binary backend/performance benchmark (#190). These are not represented as completed fixes.
