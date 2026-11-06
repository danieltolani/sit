# Dance pipeline (capture offline, render real-time)

1. **Capture** — record the dance offline. Options: video-based mocap (Rokoko Vision, Move.ai, DeepMotion, or free MediaPipe/Blender add-ons) or a mocap suit. Output: BVH or FBX.
2. **Transfer** — retarget onto the character rig in Blender (Rokoko/Auto-Rig Pro retarget, or Mixamo for quick tests). One shared humanoid skeleton means every dance works on every candidate. Keep it low-poly (<5k tris), one small texture atlas, bake the dance as an Action/clip.
3. **Export for the web** — glTF/GLB with Draco or meshopt compression (`gltf-transform optimize`). Target <500 KB per character. Put in `web/public/models/`.

Runtime: `three` (or `@react-three/fiber`) + `GLTFLoader` + `AnimationMixer`, loaded lazily as an Astro island (`client:visible`) so the page stays light. Until then `MusicalChairs.astro` uses CSS placeholders.
