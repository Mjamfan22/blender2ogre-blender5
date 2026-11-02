# blender2ogre

Blender exporter for the OGRE 3D engine.

- License: [GNU LGPL 2.1 or later](LICENSE.txt)
- [Ogre forum thread](https://forums.ogre3d.org/viewtopic.php?f=8&t=61485)
- Based on [OGRECave/blender2ogre](https://github.com/OGRECave/blender2ogre), with its original history, authors and `io_ogre` module name preserved.

This version adapts blender2ogre for **Blender 5.2.3 LTS on Windows x64**. The original project description and feature overview below are retained from upstream; our fixes and improvements are listed separately. This is an independent adaptation, not an official OGRECave release.

## Features

From the original project's import/export overview:

- Import mesh from `.xml` as well as `.mesh` files.
- Import whole `.scene` files with all their objects.
- Merge imported submeshes or keep them separate.
- Parse and convert materials into Blender using Principled BSDF materials, textures and UV mapping.
- Import poses, skeletons and animations.
- Export Blender models through **File → Export → Ogre3D (.scene and .mesh)**.
- Export materials, custom normals, vertex colors, skeletal animations, shape animations and node animations.
- Merge objects on export using collections named `merge.<yourname>` and reference external OGRE materials using `extern.<yourname>`.

See [the preserved upstream README](io_ogre/UPSTREAM_README.md) for the original project documentation and credits, and [the current usage guide](io_ogre/README.md) for this version's supported workflow and limits.

## Our fixes and improvements

- **Blender 5 support:** updated action-slot handling, named animation clips, operator initialization, registration/cleanup and installation.
- **Faster imports:** replaced expensive XML DOM searches, transferred mesh arrays in bulk and reused shared static vertex buffers. The measured example improved from **39.0 to 7.7 seconds**, retaining all triangles, eight UV layers, normals and materials. Results vary by model and computer.
- **Shared materials and textures:** added resource-pack discovery, an optional Resource Folder setting, shared material definitions and textures, imports, variables, inheritance, abstract templates and named overrides.
- **Material appearance:** corrected base-texture selection, opaque/blended/masked materials, inherited alpha rejection, image alpha, quoted texture names and renamed Principled-node lookup.
- **Texture export:** preserved packed/generated image paths and packing, and improved missing-image and optional ImageMagick diagnostics.
- **Geometry:** corrected unshared geometry, missing/unused material slots, multiple UV layers, vertex colors/alpha, custom normals, material names and skin seams. Shape-animated exports preserve their shared geometry when needed.
- **Skeletons and animation:** corrected bind matrices, bone orientation and IDs, mesh/rig bind-space conversion, clip timing, fractional frames, final samples and multiple action slots. Separate skeletons are used when shared bind spaces differ.
- **Scene import/export:** preserved nested transforms, corrected camera/light directions and projection round trips, and added linear node-animation import.
- **Export controls:** fixed Selected Only through hierarchies and merge collections; added Resource Prefix, Apply Modifiers and optional sparse node-key sampling.
- **File protection:** isolated native conversion, preserved source XML, added import rollback and staged export, and restored selection, modifiers, rig visibility, action slots and timeline state after operations.
- **Tools and diagnostics:** bundled the compatible Windows tools and license notices, repaired missing bundled/default paths, added process timeouts and configuration validation, and throttled excessive progress updates.
- **Documentation and validation:** added material/animation guidance, compatibility notes, installer checks and regression tests. All **73 release checks passed** against the installed ZIP; GitHub CI checks source, package and documentation integrity.

[Complete fixes and improvements](docs/FIXES.md) · [Version-by-version patch notes](CHANGELOG.md) · [Upstream issue audit](docs/UPSTREAM_ISSUES.md) · [Validation](docs/VALIDATION.md)

## Installing

Download `blender2ogre_Blender_5_2_v0.9.8.zip` from [Releases](https://github.com/Mjamfan22/blender2ogre-blender5/releases). In Blender, open **Edit → Preferences → Add-ons → Install from Disk**, select the ZIP, and enable **OGRE Importer-Exporter (.scene, .mesh, .skeleton)**.

Fully restart Blender after upgrading and re-import meshes created by an older importer. Keep one active `io_ogre` installation. The ZIP contains only the add-on, its documentation, licenses and bundled Windows tools.

[Installation and upgrade instructions](docs/INSTALLATION.md) · [Usage](io_ogre/README.md) · [Material mapping](io_ogre/MATERIALS.md)

## Screenshots

![Generated mesh after OGRE export and re-import](docs/images/roundtrip-demo.png)

![Imported demo in Blender](docs/images/blender-viewport.png)

The images show a generated demonstration asset after a real OGRE round trip. [Image provenance](docs/SCREENSHOTS.md).

## Development

- `io_ogre/`: installable add-on.
- `tests/`: regression tests and optional fixture instructions.
- `tools/`: packaging, verification and screenshot scripts.
- `docs/validation/`: sanitized test results and release hashes.
- `.build/`: ignored local outputs, disposable profiles and temporary files.

[Contributing and local checks](CONTRIBUTING.md) · [Review guide](docs/REVIEW.md) · [Security and tool provenance](SECURITY.md)

Windows/classic OGRE is verified. Linux native tools, full OGRENext rendering, arbitrary custom shaders, AO export, automatic compound colliders and a direct binary backend remain outside completed/verified scope. [Known limits and remaining work](docs/ROADMAP.md).

## Authors and license

Copyright (C) 2010 Brett Hartshorn and the upstream contributors. Original author credits are preserved in [the upstream README](io_ogre/UPSTREAM_README.md) and `io_ogre/__init__.py`. This adaptation retains GNU LGPL 2.1-or-later licensing and the bundled tools' original notices. [Attribution](NOTICE.md) · [License](LICENSE.txt).
