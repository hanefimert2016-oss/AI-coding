#!/usr/bin/env python3
"""Build production-ready low-poly sci-fi meshes in actual Blender and export
Godot-compatible GLB. Also save the editable .blend source and a Blender render.
Invoked by GitHub Actions: blender -b -t 2 --python blender_assets.py -- OUTDIR
"""
import bpy
import math
import pathlib
import sys
from mathutils import Vector

out_dir = pathlib.Path(sys.argv[sys.argv.index("--") + 1]).resolve()
assets = out_dir / "assets"
assets.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

materials = {}
def material(name, hexcode, metal=0.5, glow=0.0):
    if name in materials:
        return materials[name]
    color = tuple(int(hexcode[i:i+2], 16)/255.0 for i in (1,3,5))+(1,)
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = color
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = 0.28
    if glow:
        p.inputs["Emission Color"].default_value = color
        p.inputs["Emission Strength"].default_value = glow
    materials[name] = m
    return m

onyx = material("Ceramic • Midnight Carbon", "#0D1930", 0.85)
armour = material("Brushed Titanium", "#344962", 0.9)
raised = material("Royal Navy Deck", "#172D50", 0.7)
trim = material("Chrome Railings", "#8EB6CD", 0.93)
glass = material("Pilot Canopy / Turquoise", "#0A7E9A", 0.62, 0.3)
cyan = material("Hot Cyan Plasma", "#12EFFF", 0.1, 4.0)
cyan_dim = material("Sky-blue Running Lights", "#1796C9", 0.2, 2.0)
magenta = material("Magenta Warning Light", "#EC3DCF", 0.2, 4.0)
gold = material("Gold Core Hardware", "#EAA750", 0.8, 0.2)
red = material("Hostile Sentry Red", "#FF315E", 0.1, 4.0)
black = material("Engine Interior", "#07101E", 0.3)
white = material("Ceramic White", "#B7D7EE", 0.55)

ship = []
drone = []
cores = []

def apply(obj, label, mat, group, bevel=0):
    obj.name = label
    obj.data.materials.append(mat)
    group.append(obj)
    if bevel:
        bevel_mod = obj.modifiers.new("Machined Edge Radii", "BEVEL")
        bevel_mod.width = bevel
        bevel_mod.segments = 3
        obj.modifiers.new("Surface weighted normals", "WEIGHTED_NORMAL")
    return obj

def box(label, center, dims, mat, group, bevel=0.0, rz=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler.z = rz
    return apply(obj, label, mat, group, bevel)

def cyl(label, center, radius, depth, mat, group, vertices=32, bevel=0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center)
    return apply(bpy.context.object, label, mat, group, bevel)

def orb(label, center, scale, mat, group, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=center)
    obj=bpy.context.object
    obj.scale=scale
    return apply(obj,label,mat,group)

def ring(label, center, major, minor, mat, group, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=10, location=center)
    obj=bpy.context.object
    obj.rotation_euler=rotation
    return apply(obj,label,mat,group)

# Detailed two-engine racing hovercraft: integrated cockpit, nacelles, thrusters,
# aerofoils, armor plating, vents, fins, ground effect emitters and micro LED lines.
box("01 / keel • unibody", (0,0,0.25), (1.30,3.45,0.42), onyx, ship, .19)
box("02 / carbon deck", (0,-0.1,0.51), (1.15,2.67,0.16), armour, ship, .10)
box("03 / polished nose", (0,-1.62,0.32), (.83,1.12,.29), raised, ship, .12)
box("04 / cockpit lower canopy", (0,-0.62,.76), (.86,1.26,.32), glass, ship, .26)
box("05 / canopy upper", (0,-.51,.95), (.64,.83,.16), glass, ship, .11)
box("06 / cockpit armored spine", (0,.28,.77), (.20,1.18,.14), trim, ship, .045)
for side in (-1,1):
    s = "PORT" if side < 0 else "STARBOARD"
    x=side*.98
    box(s+" / turbo nacelle", (x,.48,.19), (.70,2.33,.56), armour, ship, .18)
    box(s+" / lateral intakes", (x,-.90,.26), (.61,.77,.39), onyx, ship, .12)
    box(s+" / intake spine", (x,-.89,.49), (.44,.62,.08), cyan_dim, ship, .035)
    box(s+" / wing root", (side*1.12,.72,.26), (.98,1.33,.24), raised, ship, .09, side*.12)
    box(s+" / swept blade", (side*1.55,.66,.18), (.91,.77,.13), armour, ship, .06, side*.38)
    box(s+" / blade emissive ribbon", (side*1.65,.82,.28), (.51,.53,.05), cyan, ship, .018, side*.32)
    box(s+" / rear swept canard", (side*.81,1.41,.31), (.37,.79,.13), onyx, ship, .07, side*.20)
    cyl(s+" / engine combustion chamber", (x,1.57,.18), .28, .43, black, ship, 40, .045)
    ring(s+" / circular thruster", (x,1.79,.18), .27,.06,cyan,ship,(math.pi/2,0,0))
    orb(s+" / plasma ion exhaust", (x,1.76,.18), (.19,.06,.19), cyan_dim, ship)
    for n in range(5):
        box(s+f" / heat vent {n+1:02}", (x,-.12+n*.23,.50),
            (.45,.056,.04),black,ship,.008)
    for n in range(3):
        box(s+f" / micro radiator {n+1:02}", (side*1.20,.35+n*.34,.52),
            (.23,.11,.13),trim,ship,.018)
    box(s+" / graphite skid", (side*.79,-.02,-.18),(.16,2.28,.11),black,ship,.06)
    box(s+" / magnetic pad rail",(side*.79,-.10,-.26),(.11,1.5,.04),cyan_dim,ship,.02)
    for n in range(4):
        orb(s+f" / status diode {n+1:02}",
            (side*.55,-1.0+n*.33,.62),(.04,.04,.026),
            magenta if n == 0 else cyan,ship)

for n in range(6):
    box(f"rear armor fin {n+1}", (-.46+n*.18,1.54,.52),(.11,.47,.17),
        armour,ship,.025)
cyl("central inertial stabilizer", (0,.56,.61),.21,.12,gold,ship,36,.035)
ring("inertial ring", (0,.56,.72),.19,.028,cyan,ship)

def export(group, name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in group:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = group[0]
    fn=assets / (name+".glb")
    bpy.ops.export_scene.gltf(
        filepath=str(fn),
        export_format='GLB',
        use_selection=True,
        export_materials='EXPORT'
    )
    print("BLENDER_EXPORTED",str(fn),fn.stat().st_size,"bytes",len(group),"objects")

export(ship,"ship")

# A model distinct from the ship: six-arm guardian drone with red lidar rings.
cyl("Sentry Main Reactor", (0,0,.0), .55,.37,armour,drone,16,.08)
orb("Sentry iris • target scanner", (0,-.11,.20),(.4,.39,.28),red,drone)
ring("Hazard holo-ring",(0,0,.08),.63,.045,red,drone)
for i in range(6):
    angle=math.tau*i/6
    x=math.cos(angle)*.8; y=math.sin(angle)*.8
    box(f"Sentry armoured rotor strut {i}",(x,y,.08),(.75,.17,.18),onyx,drone,.06,angle)
    orb(f"Sentry thruster {i}",(x*1.24,y*1.24,.03),(.17,.17,.15),red,drone)
    box(f"Sentry armour {i}",(x*.62,y*.62,.27),(.32,.19,.12),trim,drone,.045,angle)
cyl("Sentry antenna",(0,0,.48),.04,.46,trim,drone,16)
orb("Sentry antenna LED",(0,0,.75),(.085,.085,.085),red,drone)
export(drone,"drone")

# Energy pickup: prismatic golden reactor with blue orbitals.
orb("Energy reactor heart",(0,0,0),(.45,.45,.45),cyan,cores,24,16)
ring("Core orbital • horizontal",(0,0,0),.59,.053,gold,cores)
ring("Core orbital • vertical",(0,0,0),.62,.037,white,cores,(math.pi/2,0,0))
ring("Core orbital • diagonal",(0,0,0),.71,.025,cyan_dim,cores,(.73,.63,0))
for i in range(6):
    z=.62 if i<3 else -.62
    a=math.tau*(i%3)/3
    orb(f"floating conduit node {i}",(math.cos(a)*.31,math.sin(a)*.31,z),
        (.07,.07,.07),gold,cores,12,8)
export(cores,"core")

# Assemble one editable .blend "asset development studio" with all 3 assets.
for obj in drone:
    obj.location.x += 4.5
for obj in cores:
    obj.location.x -= 4.5
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.58))
floor=bpy.context.object
floor.name="Product photography cyclorama floor"
floor.data.materials.append(black)
light=bpy.data.lights.new("Studio • key",type="AREA")
light.energy=3000
light.shape="DISK"
light.size=6
obj=bpy.data.objects.new("Key softbox",light)
bpy.context.collection.objects.link(obj)
obj.location=(1,-5,8)

light2=bpy.data.lights.new("Studio • cool rim",type="AREA")
light2.energy=2000
light2.color=(.3,.8,1)
light2.size=5
obj2=bpy.data.objects.new("Cyan rim light",light2)
bpy.context.collection.objects.link(obj2)
obj2.location=(-4,4,6)

camera=bpy.data.cameras.new("Lens / 50mm")
camera_obj=bpy.data.objects.new("Showcase • hero camera",camera)
bpy.context.collection.objects.link(camera_obj)
camera_obj.location=(8,-12,8)
towards=Vector((0,.1,.2)) - camera_obj.location
camera_obj.rotation_euler=towards.to_track_quat('-Z','Y').to_euler()
bpy.context.scene.camera=camera_obj
camera.type="ORTHO"
camera.ortho_scale=11.5
bpy.context.scene.render.resolution_x=1280
bpy.context.scene.render.resolution_y=720
bpy.context.scene.render.resolution_percentage=100
bpy.context.scene.render.image_settings.file_format="PNG"
bpy.context.scene.render.engine="BLENDER_WORKBENCH"
bpy.context.scene.display.shading.light='STUDIO'
bpy.context.scene.display.shading.color_type="MATERIAL"
bpy.context.scene.display.shading.show_shadows=True
bpy.context.scene.display.shading.show_cavity=True
bpy.context.scene.display.shading.cavity_type="BOTH"
bpy.context.scene.display.shading.background_type='WORLD'
bpy.context.scene.world.color=(.023,.03,.055)
bpy.context.scene.render.filepath=str(out_dir/"blender-asset-preview.png")
bpy.ops.render.render(write_still=True)

blend_file=out_dir/"NEON-CIRCUIT-Blender-Assets.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
print("BLENDER_SOURCE_CREATED",blend_file,blend_file.stat().st_size)
print("BLENDER_RENDER_CREATED",bpy.context.scene.render.filepath)
