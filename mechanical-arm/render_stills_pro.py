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
scene.cycles.samples=48
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.view_settings.view_transform='AgX' if 'AgX' in [x.identifier for x in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
try:
    bpy.context.view_layer.cycles.use_denoising=False
except Exception: pass
cam=scene.camera
target=Vector((.45,0,.91))
for name, position, scale, target in [
    ("AXIOM-6-PRO-Hero-Render.png", (3.0,-4.9,2.50),2.88,Vector((.47,0,.91))),
    ("AXIOM-6-PRO-Technical-Side.png", (3.9,-2.10,2.20),2.90,Vector((.47,0,.91))),
    ("AXIOM-6-PRO-Gripper-Closeup.png",(2.65,-2.32,2.10),1.13,Vector((1.03,0,1.57))),
]:
    cam.location=position
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale
    scene.render.filepath=os.path.join(out,name)
    bpy.ops.render.render(write_still=True)
    assert os.stat(scene.render.filepath).st_size>10000
    print("AXIOM_RENDER",scene.render.filepath,os.stat(scene.render.filepath).st_size,flush=True)
