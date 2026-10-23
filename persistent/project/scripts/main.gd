extends Node3D
## NEON CIRCUIT: a complete small 3D arcade collect-and-survive game.
## 3D hovercraft, sentry drones and energy core meshes are authored in Blender,
## exported as glTF and instantiated in this playable Godot level.

const REQUIRED: int = 8
const ROUND_SECONDS: float = 90.0
const ARENA_RADIUS: float = 22.0

var craft: Node3D
var chase_camera: Camera3D
var cores: Array[Node3D] = []
var enemies: Array[Node3D] = []
var core_home: Array[Vector3] = []
var speed: Vector3 = Vector3.ZERO
var heading: float = 0.0
var elapsed: float = 0.0
var collected: int = 0
var health: int = 100
var active: bool = true
var hit_cooldown: float = 0.0
var accent_time: float = 0.0
var score_label: Label
var telemetry_label: Label
var status_label: Label
var top_label: Label
var mission_box: PanelContainer
var alert_label: Label
var demo_mode: bool = false


func _ready() -> void:
    demo_mode = OS.has_feature("editor") and OS.get_cmdline_user_args().has("--demo")
    _setup_environment()
    _create_city()
    _create_flyer()
    _place_collectibles()
    _create_sentries()
    _setup_camera()
    _create_hud()
    print("NEON_CIRCUIT_READY")
    print("BLENDER_SHIP_MESH_INSTANCED=", craft != null)
    print("COLLECTIBLE_COUNT=", cores.size())
    print("ENEMY_COUNT=", enemies.size())


func _mat(tint: Color, glow: float = 0.0, metallic: float = 0.25) -> StandardMaterial3D:
    var mat := StandardMaterial3D.new()
    mat.albedo_color = tint
    mat.metallic = metallic
    mat.roughness = 0.38
    if glow > 0.0:
        mat.emission_enabled = true
        mat.emission = tint
        mat.emission_energy_multiplier = glow
    return mat


func _cuboid(label_text: String, where: Vector3, size: Vector3, tint: Color, glow: float = 0.0) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = label_text
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _mat(tint, glow)
    node.position = where
    add_child(node)
    return node


func _column(where: Vector3, radius: float, height: float, tint: Color, glow: float = 0.0) -> MeshInstance3D:
    var mesh := CylinderMesh.new()
    mesh.top_radius = radius
    mesh.bottom_radius = radius
    mesh.height = height
    var pillar := MeshInstance3D.new()
    pillar.mesh = mesh
    pillar.material_override = _mat(tint, glow)
    pillar.position = where
    add_child(pillar)
    return pillar


func _setup_environment() -> void:
    var world := WorldEnvironment.new()
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#060b1c")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#7893d9")
    env.ambient_light_energy = 0.9
    world.environment = env
    add_child(world)

    var moon := DirectionalLight3D.new()
    add_child(moon)
    moon.rotation_degrees = Vector3(-60, -30, 0)
    moon.light_color = Color("#7b9ce7")
    moon.light_energy = 1.2

    var red := OmniLight3D.new()
    red.position = Vector3(0, 5, -15)
    red.light_color = Color("#e63fbc")
    red.light_energy = 2.5
    red.omni_range = 27
    add_child(red)

    var cyan := OmniLight3D.new()
    cyan.position = Vector3(-9, 4, 6)
    cyan.light_color = Color("#08d9ff")
    cyan.light_energy = 2.1
    cyan.omni_range = 26
    add_child(cyan)


func _create_city() -> void:
    _cuboid("Obsidian arena", Vector3(0, -0.63, 0), Vector3(51, 1.25, 51), Color("#111e34"))
    _cuboid("Arena perimeter lower", Vector3(0, -1.33, 0), Vector3(55, 0.22, 55), Color("#041225"), 0.25)
    _cuboid("Arena north boundary", Vector3(0, 0.12, -25), Vector3(51, 0.24, 0.17), Color("#02e7fa"), 2.0)
    _cuboid("Arena south boundary", Vector3(0, 0.12, 25), Vector3(51, 0.24, 0.17), Color("#02e7fa"), 2.0)
    _cuboid("Arena east boundary", Vector3(25, 0.12, 0), Vector3(0.17, 0.24, 51), Color("#e13eea"), 2.0)
    _cuboid("Arena west boundary", Vector3(-25, 0.12, 0), Vector3(0.17, 0.24, 51), Color("#e13eea"), 2.0)

    for i in range(-12, 13):
        var pos: float = float(i) * 2.0
        _cuboid("Cyan grid %d" % i, Vector3(pos, 0.019, 0), Vector3(0.035, 0.023, 49), Color("#08788d"), 0.7)
        _cuboid("Violet grid %d" % i, Vector3(0, 0.02, pos), Vector3(49, 0.02, 0.035), Color("#3d3c98"), 0.65)

    for i in range(24):
        var a: float = TAU * float(i) / 24.0
        var radius: float = 33.0 + 2.0 * float(i % 4)
        var height: float = 8.0 + float((i * 7) % 23)
        var where := Vector3(cos(a) * radius, height / 2.0 - 1.0, sin(a) * radius)
        var tone := Color("#12233b") if i % 3 != 0 else Color("#221d43")
        _cuboid("Skyline mega tower %02d" % i, where, Vector3(3.8, height, 3.8), tone)
        _cuboid("Tower glowing crown %02d" % i,
            where + Vector3(0, height / 2.0 + 0.05, 0),
            Vector3(3.9, 0.24, 3.9),
            Color("#06dff4") if i % 2 == 0 else Color("#ec53d7"), 1.8)
        for level in range(1, int(height / 3.5)):
            _cuboid("Tower window %d-%d" % [i,level],
                Vector3(where.x, level * 3.5 - 1.5, where.z - 1.95),
                Vector3(2.8, 0.12, 0.07), Color("#1c719f"), 0.6)

    for i in range(12):
        var a: float = TAU * float(i) / 12.0
        var where := Vector3(cos(a) * 22.0, 0.05, sin(a) * 22.0)
        _column(where, 1.6, 0.14, Color("#a430a5"), 1.2)
        _column(where + Vector3(0,1.15,0), 0.15, 2.1, Color("#5aeaf9"), 1.0)
        _column(where + Vector3(0,2.27,0), 0.35, 0.18, Color("#fb4cdb"), 1.6)

    # Triangular lines give the level more depth than a flat checkerboard.
    for i in range(10):
        var a: float = TAU * float(i) / 10.0
        var stripe := _cuboid("Radial runway %d" % i,
            Vector3(cos(a) * 17.0, 0.055, sin(a) * 17.0),
            Vector3(0.10, 0.025, 6.6), Color("#cb3ad1"), 1.2)
        stripe.rotation.y = a + PI / 2.0


func _create_flyer() -> void:
    var source: PackedScene = load("res://assets/ship.glb")
    craft = source.instantiate() as Node3D
    craft.name = "BLENDER_BUILT_PLAYABLE_HOVERSHIP"
    add_child(craft)
    craft.position = Vector3(0, 1.15, 6)

    var light := OmniLight3D.new()
    light.light_color = Color("#04e8ff")
    light.light_energy = 2.2
    light.omni_range = 7.0
    craft.add_child(light)
    light.position = Vector3(0,0.4,0)


func _place_collectibles() -> void:
    var shard_source: PackedScene = load("res://assets/core.glb")
    for i in range(16):
        var theta: float = TAU * (float(i) + 0.35) / 16.0
        var radius: float = 8.0 if i % 2 == 0 else 16.0
        var pos := Vector3(cos(theta) * radius, 1.5, sin(theta) * radius)
        var collectible := shard_source.instantiate() as Node3D
        collectible.name = "Energy Core %02d" % (i + 1)
        collectible.position = pos
        collectible.scale = Vector3.ONE * 0.78
        add_child(collectible)
        cores.append(collectible)
        core_home.append(pos)


func _create_sentries() -> void:
    var drone_source: PackedScene = load("res://assets/drone.glb")
    for i in range(5):
        var theta: float = TAU * float(i) / 5.0
        var drone := drone_source.instantiate() as Node3D
        drone.name = "Sentry %d" % (i + 1)
        drone.position = Vector3(cos(theta) * 19.0, 1.2, sin(theta) * 19.0)
        add_child(drone)
        enemies.append(drone)


func _setup_camera() -> void:
    chase_camera = Camera3D.new()
    chase_camera.name = "CinematicFollowCam"
    chase_camera.fov = 67.0
    chase_camera.position = Vector3(22, 24, 30)
    add_child(chase_camera)
    chase_camera.look_at(Vector3(0,0,0), Vector3.UP)
    chase_camera.current = true


func _new_label(text_value: String, size: int, color: Color, pos: Vector2) -> Label:
    var label := Label.new()
    label.text = text_value
    label.position = pos
    label.add_theme_font_size_override("font_size", size)
    label.add_theme_color_override("font_color", color)
    return label


func _create_hud() -> void:
    var hud := CanvasLayer.new()
    hud.layer = 5
    add_child(hud)

    var top_band := ColorRect.new()
    top_band.color = Color(0.02, 0.045, 0.095, 0.88)
    top_band.position = Vector2.ZERO
    top_band.size = Vector2(1280, 105)
    hud.add_child(top_band)

    var edge := ColorRect.new()
    edge.color = Color("#06e9ff")
    edge.position = Vector2(0, 103)
    edge.size = Vector2(1280, 2)
    hud.add_child(edge)

    hud.add_child(_new_label("◆  N E O N   C I R C U I T", 33, Color("#c8f9ff"), Vector2(38, 16)))
    hud.add_child(_new_label("H Y P E R D R I V E    /    S E C T O R   0 7", 12, Color("#44bbd4"), Vector2(40, 63)))

    score_label = _new_label("0 / 8", 32, Color("#00f7fb"), Vector2(830, 17))
    hud.add_child(score_label)
    hud.add_child(_new_label("ENERGY CORES", 13, Color("#93bccb"), Vector2(830, 65)))

    telemetry_label = _new_label("100%  |  01:30", 27, Color("#ffcc7a"), Vector2(1030, 22))
    hud.add_child(telemetry_label)
    hud.add_child(_new_label("HULL  /  TIME", 13, Color("#93bccb"), Vector2(1030, 65)))

    var bottom := ColorRect.new()
    bottom.color = Color(0.02, 0.04, 0.09, 0.90)
    bottom.position = Vector2(0, 658)
    bottom.size = Vector2(1280, 62)
    hud.add_child(bottom)
    status_label = _new_label("W A S D / A R R O W S   •   DRIVE        /        COLLECT 8 CORES        /        EVADE RED SENTRIES",
        15, Color("#bbcedd"), Vector2(33, 675))
    hud.add_child(status_label)

    alert_label = _new_label("SYSTEM ONLINE   •   BLENDER ASSETS LOADED", 19, Color("#4af2ff"), Vector2(40, 125))
    hud.add_child(alert_label)

    var corner := ColorRect.new()
    corner.color = Color("#d93be8")
    corner.position = Vector2(30, 150)
    corner.size = Vector2(210, 3)
    hud.add_child(corner)


func _physics_process(delta: float) -> void:
    elapsed += delta
    if craft == null:
        return
    if hit_cooldown > 0.0:
        hit_cooldown -= delta

    var direction := Vector2.ZERO
    if active:
        if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
            direction.x -= 1
        if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
            direction.x += 1
        if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
            direction.y -= 1
        if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
            direction.y += 1
        if direction.length() > 0.1:
            direction = direction.normalized()
        if demo_mode and direction == Vector2.ZERO:
            direction = Vector2(sin(elapsed * 0.75), -cos(elapsed * 0.75)) * 0.8

    var target_speed := Vector3(direction.x, 0, direction.y) * 11.0
    speed = speed.lerp(target_speed, minf(delta * 3.1, 1.0))
    craft.position += speed * delta
    craft.position.x = clampf(craft.position.x, -23.0, 23.0)
    craft.position.z = clampf(craft.position.z, -23.0, 23.0)
    craft.position.y = 1.15 + sin(elapsed * 3.4) * 0.12

    if speed.length() > 0.5:
        heading = lerp_angle(heading, atan2(speed.x, speed.z), delta * 5.0)
    craft.rotation.y = heading
    craft.rotation.z = lerpf(craft.rotation.z, -direction.x * 0.18, delta * 3.6)
    craft.rotation.x = lerpf(craft.rotation.x, direction.y * 0.1, delta * 3.6)

    var desired := craft.position + Vector3(21.0, 23.0, 29.0)
    chase_camera.position = chase_camera.position.lerp(desired, minf(delta * 1.7, 1.0))
    chase_camera.look_at(craft.position + Vector3(0.0, 0.5, 0.0), Vector3.UP)

    for i in range(cores.size()):
        var core := cores[i]
        if not is_instance_valid(core):
            continue
        core.rotate_y(delta * 1.5)
        core.position.y = core_home[i].y + sin(elapsed * 2.1 + float(i)) * 0.16
        if active and core.position.distance_to(craft.position) < 2.0:
            core.queue_free()
            collected += 1
            alert_label.text = "ENERGY CAPTURED   +1  /  SYSTEM CHARGING"
            if collected >= REQUIRED:
                active = false
                alert_label.text = "MISSION COMPLETE  /  HYPERDRIVE CHARGED!"

    for i in range(enemies.size()):
        var enemy := enemies[i]
        if not is_instance_valid(enemy):
            continue
        var towards := craft.position - enemy.position
        towards.y = 0
        if active and towards.length() > 1.7:
            enemy.position += towards.normalized() * delta * (1.2 + float(i) * 0.3)
        enemy.position.y = 1.28 + sin(elapsed * 3.2 + float(i)) * 0.23
        enemy.rotation.y += delta * (1.1 + float(i) * 0.2)
        if active and towards.length() < 2.3 and hit_cooldown <= 0.0:
            health = maxi(health - 16, 0)
            hit_cooldown = 1.6
            alert_label.text = "WARNING   /   SENTINEL COLLISION   /   SHIELDS DAMAGED"
            if health <= 0:
                active = false
                alert_label.text = "SYSTEM FAILURE  /  PRESS R TO RESTART"

    if active and elapsed >= ROUND_SECONDS:
        active = false
        alert_label.text = "TIME EXPIRED  /  PRESS R TO RETRY"

    if Input.is_key_pressed(KEY_R):
        get_tree().reload_current_scene()

    score_label.text = "%02d / %02d" % [collected, REQUIRED]
    var remaining: int = maxi(int(ceil(ROUND_SECONDS - elapsed)), 0)
    telemetry_label.text = "%03d%%  |  %02d:%02d" % [health, int(remaining / 60), remaining % 60]
    if not active:
        status_label.text = "M I S S I O N  E N D E D     •     P R E S S   R   T O   R E S T A R T"
