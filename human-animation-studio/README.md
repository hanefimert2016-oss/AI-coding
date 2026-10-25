# KINETIC HUMAN — rigged Blender character and animation studio

This is a standalone **human 3D model**, not a video game. Constructed from original procedural organic human geometry inside Blender.

## Files (saved to `human-animation-studio/output/`)
- `KINETIC-HUMAN-Rigged-Animated.blend` — editable Blender project containing armature and actions
- `KINETIC-HUMAN-Rigged-Animated.glb` — portable glTF 2.0 binary with skeletal skin and animations
- `KINETIC-HUMAN-Real-Blender-Creation-And-Animations.mp4` — real captured Blender GUI (model creation and animation previews)
- `KINETIC-HUMAN-01-Idle.png` / `02-Walk.png` / `03-Run.png` / `04-Punch.png` — studio Cycles character pose renders
- `Modeling-Progress-Contact-Sheet.jpg` — four frames sampled from actual screen capture
- `rig-animation-check.json` and `video-metadata.txt` — structural validation results

## Skeletal actions
`Idle_Breathing`: 96-frame breathing cycle.
`Walk_Loop`: 48-frame walk cycle.
`Run_Loop`: 32-frame run cycle.
`Punch_Right_Jab`: 48-frame right-hand boxing jab.

The character is fully rigged with Blender Armature, mesh vertex groups, smooth organic limbs and separate facial details. All meshes are deformed by the skeleton (including hands, shoes and face).

## Running Blender locally
1. Open the `.blend` file in Blender 4.x.
2. Select `KINETIC_HUMAN_RIG`.
3. Open the **Dope Sheet > Action Editor** and choose one of the four named actions.
4. Move/play the timeline to animate the human. For loops, the animation names and sample lengths are listed above.
5. Import the `.glb` in any compatible engine/editor that supports glTF 2.0 skins and actions.

The GitHub workflow at `.github/workflows/kinetic-human-animation.yml` creates all output on ordinary GitHub hosted runners, not on the user's computer. The MP4 records the Blender application window, not a generated slideshow.
