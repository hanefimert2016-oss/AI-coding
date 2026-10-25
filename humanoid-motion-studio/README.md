# AETHER-01 — Rigged Human Character

An original procedural stylized humanoid modeled inside **Blender 4.0**. Not a video game; the deliverables are a skeletal 3D character, armature animations, Blender source, screenshots and videos.

## What the model includes
- Skeletal armature (root, hips, spine, chest, neck, head, two legs and feet, two arms and hands, three independently rigged fingers per hand)
- Natural stylized head with scalp, cheeks, ears, hair, eyebrows, eyes, nose and mouth
- Contemporary techwear jacket, fitted running leggings, panel details, belt and athletic sneakers
- Meshes weighted to the armature via deform vertex groups; the GLB contains **glTF skins**
- Separately authored Blender actions: **Idle**, **Walk**, **Run**, **Punch**
- Real screen recording of Blender automatically modeling and rigging the human
- An additional MP4 that shows the Blender skeleton actually moving with the four actions
- Five character pose renders: neutral, walking, running, punching, close-up portrait

## Downloads

The workflow puts verified outputs into [outputs/](https://github.com/hanefimert2016-oss/AI-coding/tree/aether-humanoid-rig-20261025/humanoid-motion-studio/outputs).

- `AETHER-01-Rigged-Animated-Human.glb`: portable glTF 2.0 model, skin + animation clips
- `AETHER-01-Rigged-Animated-Human.blend`: original editable Blender project, bones, objects and animation Actions
- `AETHER-01-Blender-Modeling-Rigging-Process.mp4`: genuine recorded X11 Blender modeling process
- `AETHER-01-Idle-Walk-Run-Punch-Demo.mp4`: actual Blender-rendered skeleton motion sampler
- `01-...` through `05-...` PNG renders, plus GUI construction screenshots

## Blender use

Open the .blend in Blender. Select object `AETHER_01_DEFORM_RIG`, go to Dope Sheet → Action Editor, and switch among the actions named Idle, Walk, Run and Punch. Unmute or disable NLA tracks as needed. Use Space to play and Ctrl+Space for fullscreen.

To make the motions appear in an imported GLB, enable skinning + animation import in the target engine; select each named glTF animation. Existing workflow also verifies all four motion clips and glTF skin nodes are embedded, and tests both MP4 files by fully decoding them.

### Fidelity notes

This is an original **stylized** human in techwear, not a photorealistic scan. Limb garment sections are segmented, with each piece bound to a designated bone: convenient for procedural customization but not a substitute for continuous subdivision/weight-painted skin with facial blendshapes. The 3D geometry is Blender mesh, not a generated picture.

Model creation is deterministic, source code: `character_builder.py`. Render and animation frames script: `render_poses_and_motion.py`.
