extends Node3D

# A real playable minimal 3D world. The CI run number is persisted between
# GitHub-hosted runs in res://data/ci_state.json on the dedicated state branch.

var pilot: MeshInstance3D
var crystals: Array[MeshInstance3D] = []
var hud: Label
var score: int = 0
var run_number: int = 0
var elapsed: float = 0.0


func _ready() -> void:
    var state_path := "res://data/ci_state.json"
    if FileAccess.file_exists(state_path):
        var file := FileAccess.open(state_path, FileAccess.READ)
        var state = JSON.parse_string(file.get_as_text())
        if typeof(state) == TYPE_DICTIONARY:
            run_number = int(state.get("run_number", 0))
    print("PERSISTED_RUN_NUMBER=", run_number)
    _build_world()
    print("GODOT_WORLD_READY")


func _build_world() -> void:
    var sky := WorldEnvironment.new()
    var environment := Environment.new()
    environment.background_mode = Environment.BG_COLOR
    environment.background_color = Color("#08111f")
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("#8198c9")
    environment.ambient_light_energy = 0.8
    sky.environment = environment
    add_child(sky)

    var sunlight := DirectionalLight3D.new()
    sunlight.rotation_degrees = Vector3(-55.0, -35.0, 0.0)
    sunlight.light_energy = 2.2
    add_child(sunlight)

    _box("Platform", Vector3(0, -0.35, 0), Vector3(22, 0.7, 22), Color("#16263c"))
    for i in range(11):
        _box("GridZ%02d" % i, Vector3(-10 + i * 2, 0.008, 0), Vector3(0.025, 0.01, 21), Color("#145579"))
        _box("GridX%02d" % i, Vector3(0, 0.008, -10 + i * 2), Vector3(21, 0.01, 0.025), Color("#145579"))

    for i in range(12):
        var theta := float(i) / 12.0 * TAU
        var radius := 5.5 + float(i % 3) * 1.0
        var shard := _box("EnergyCell%02d" % i,
            Vector3(cos(theta) * radius, 0.65, sin(theta) * radius),
            Vector3(0.65, 1.3, 0.65), Color("#05d6f4"))
        crystals.append(shard)

    pilot = _box("Pilot", Vector3(0, 0.9, 0), Vector3(0.9, 1.8, 0.9), Color("#f0a746"))
    _box("Beacon", Vector3(0, 2.75, 0), Vector3(0.2, 0.2, 0.2), Color("#ffdf7a"))

    var camera := Camera3D.new()
    camera.name = "OrbitCamera"
    camera.position = Vector3(0, 13, 17)
    camera.look_at(Vector3(0, 0.0, 0), Vector3.UP)
    camera.current = true
    add_child(camera)

    var overlay := CanvasLayer.new()
    add_child(overlay)
    hud = Label.new()
    hud.position = Vector2(24, 24)
    hud.add_theme_color_override("font_color", Color("#d8f9ff"))
    hud.add_theme_font_size_override("font_size", 23)
    overlay.add_child(hud)
    _refresh_hud()


func _box(box_name: String, at: Vector3, size: Vector3, tint: Color) -> MeshInstance3D:
    var instance := MeshInstance3D.new()
    instance.name = box_name
    var box_mesh := BoxMesh.new()
    box_mesh.size = size
    instance.mesh = box_mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = tint
    material.metallic = 0.25
    material.roughness = 0.33
    instance.material_override = material
    instance.position = at
    add_child(instance)
    return instance


func _physics_process(delta: float) -> void:
    elapsed += delta
    if pilot == null:
        return
    var axis := Vector2(
        Input.get_action_strength("ui_right") - Input.get_action_strength("ui_left"),
        Input.get_action_strength("ui_down") - Input.get_action_strength("ui_up")
    )
    if axis.length_squared() > 0.0:
        axis = axis.normalized()
        pilot.position += Vector3(axis.x, 0, axis.y) * delta * 5.0
        pilot.position.x = clampf(pilot.position.x, -9.5, 9.5)
        pilot.position.z = clampf(pilot.position.z, -9.5, 9.5)
    for shard in crystals:
        if is_instance_valid(shard):
            shard.rotation.y += delta * 1.1
            if pilot.position.distance_to(shard.position) < 1.1:
                shard.queue_free()
                score += 1
                _refresh_hud()


func _refresh_hud() -> void:
    if hud != null:
        hud.text = "J.A.R.V.I.S. / GODOT 4.7.2  |  RUN #%d\nWASD / ARROWS: move  |  ENERGY: %d / 12" % [run_number, score]
