# NEON CIRCUIT — Godot + Blender game

A real 3D arcade hovercraft arena, authored by procedural Blender mesh creation and a playable Godot scene.

## Features
- Blender-made 3D hovercraft with detailed nacelles, aerodynamic fins, cockpit canopy, micro-LEDs, plasma exhaust.
- Blender-made sentry enemies with multiple arms and emissive red rings.
- Blender-made rotating energy orbs; gather **eight** to power up the hyperdrive.
- Enemies track you and damage your hull when colliding. Survive the 90-second deadline.
- Wide futuristic neon arena, skyline towers, wayfinding grid, lighting, anti-gravity motion, third-person camera.
- Designed at 1280×720. **WASD/arrow keys** move; **R** restarts.
- Model sources available as editable `.blend`, Godot imports individual `.glb` models.

## How to get it
The complete playable Godot project, Blender source, MP4 and PNG screenshots are committed to the dedicated branch once the actual GitHub workflow verifies the game:

[Persistent project](https://github.com/hanefimert2016-oss/AI-coding/tree/godot-persistent-state/persistent/project)

[MP4 and screenshots](https://github.com/hanefimert2016-oss/AI-coding/tree/godot-persistent-state/persistent/showcase/neon-circuit)

[GitHub Actions video recording and 3D asset build](https://github.com/hanefimert2016-oss/AI-coding/actions/workflows/neon-circuit-game.yml)

## Build and video workflow
1. Normal GitHub-hosted Ubuntu runner restores previous run number.
2. Runs real `blender -b --python` to produce `ship.glb`, `core.glb`, `drone.glb` and editable .blend.
3. Runs Godot 4.7.2 `--editor --import`; tests playable scene and loaded meshes.
4. Launches real Blender and Godot graphical desktop on Xvfb with Mesa software OpenGL.
5. Records an actual X11 desktop session with `ffmpeg -f x11grab`, pressing movement keys using xdotool.
6. Stores video, PNG screenshots, Blender project, actual Godot assets and run metadata in `godot-persistent-state` branch.
7. The previously configured general Godot runner reloads `persistent/project/` on its next invocation; generated model assets persist.

No Unity login, Unity licence, self-hosted runner, AI asset API or proprietary game engine needed.
