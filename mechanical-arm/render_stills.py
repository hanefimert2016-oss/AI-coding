#!/usr/bin/env python3
"""Offline studio stills from the actual editable AXIOM-6 Blender scene."""
import bpy, math, os, sys
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=os.path.abspath(args[0] if args else "/tmp/axiom6")
os.makedirs(out,exist_ok=True)
scene=bpy.context.scene
scene.render.resolution_x=1600
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.view_settings.view_transform='AgX' if 'AgX' in [x.identifier for x in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
try:
    bpy.context.view_layer.cycles.use_denoising=False
except Exception: pass
cam=scene.camera
target=Vector((.40,0,.89))
for name, position, scale in [
    ("AXIOM-6-Hero-Render.png", (3.2,-4.6,2.70),3.25),
    ("AXIOM-6-Technical-Side.png", (3.4,-2.9,2.06),3.1),
]:
    cam.location=position
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale
    scene.render.filepath=os.path.join(out,name)
    bpy.ops.render.render(write_still=True)
    assert os.stat(scene.render.filepath).st_size>10000
    print("AXIOM_RENDER",scene.render.filepath,os.stat(scene.render.filepath).st_size,flush=True)
