# FBX Bundler

The built in Blender FBX exporter requires you to embed all textures in the FBX if you want the export to be linked properly which leads to a very large FBX file. This Blender add-on allows you to export an FBX with all textures bundled and linked properly in a separate folder. This helps you easily export many objects and textures as a single FBX for importing into a game engine like Unity.

## Features

- Copies textures used by exported objects into a folder next to the FBX, with relative paths in the file
- Unity mask map packing (R=Metallic, G=AO, A=Smoothness), optionally skipping the source PBR textures
- Texture conversion: PNG, JPEG, TGA, or WebP, with max resolution limit
- Presets for Unity, Unreal, Godot, and Blender
- Batch export to make one FBX per selected object
- Option to preserve the texture folder structure instead of flattening
