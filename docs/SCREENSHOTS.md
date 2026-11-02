# Image provenance

- **roundtrip-demo.png**: a Blender render of a generated demonstration mesh after classic OGRE export and re-import with this add-on. The checker texture is generated locally. It illustrates retained geometry/UV/materials; it is not an OGRE game-engine render.
- **blender-viewport.png**: an actual window capture of the imported synthetic demonstration in a separate, isolated Blender 5.2 session, using Blender's native screenshot operator. Solid material colors are shown in the viewport; the rendered image above shows the actual image texture. Existing user scenes/preferences are not used.
- **import-performance.svg**: a chart drawn from the documented v0.9.6/v0.9.7 measurements, not a screenshot or a simulated runtime result. Read the measurement conditions in the validation guide.

The image creation script is `ChatGPT/tools/make_review_demo.py`. Run it through `ChatGPT/tools/run_blender.py` using the verified Blender version, then run `ChatGPT/tools/open_review_preview.py --blender PATH` to open the generated .blend in an isolated profile and capture the viewport. The preview closes itself after capture. The .blend and generated export files are temporary development outputs, not installer contents. No external model-pack content is shown.
