# Godot Starter World

This project is a working, minimal 3D Godot 4.7.2 game demonstrating persistence through GitHub Actions. It includes a controllable orange avatar, a 3D arena, pickups, HUD and simulated lighting.

- Code: `scripts/world.gd`
- Start scene: `scenes/main.tscn`
- CI persistence counter: `data/ci_state.json`
- Gameplay movement: Arrow keys (and WASD if bound in Input Map)

The **starter files in this folder are only used when the persistent state branch is empty**. After the first successful run, edit the game in the `godot-persistent-state` branch under `persistent/project/` to ensure modifications are restored in subsequent runs.

CI engine logs, screenshots, file manifests and testing state: `godot-persistent-state:persistent/run-history/`.

The full workflow and persistence details are at the root `GODOT_PERSISTENT_SYSTEM.md`.
