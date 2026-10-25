#!/usr/bin/env python3
"""Render four pose demonstrations from real NOVA Blender armature animation NLA."""
import bpy,sys,os,math
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT=os.path.abspath(args[0] if args else "/tmp/nova")
os.makedirs(OUT,exist_ok=True)
scene=bpy.context.scene
rig=bpy.data.objects.get("NOVA / 22-Bone Motion Skeleton")
assert rig and rig.type=="ARMATURE"
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=28
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=1400
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
try:bpy.context.view_layer.cycles.use_denoising=False
except Exception:pass
for name,frame,camera,scale in [
    ("01-NOVA-Full-Body-Idle.png",6,(3.5,-5.8,2.6),2.68),
    ("02-NOVA-Walk-Cycle.png",7,(3.2,-5.3,2.2),2.60),
    ("03-NOVA-Run-Cycle.png",6,(3.3,-5.8,2.48),2.68),
    ("04-NOVA-Punch-Action.png",15,(3.4,-5.9,2.45),2.65),
]:
    chosen=name.split("-")[2] if name.startswith("0") else "Idle"
    if chosen=="Full":chosen="Idle"
    # Filename tokens are Idle, Walk, Run, Punch as last purpose.
    if "Idle" in name:chosen="Idle"
    elif "Walk" in name:chosen="Walk"
    elif "Run" in name:chosen="Run"
    else:chosen="Punch"
    tracks=rig.animation_data.nla_tracks
    for t in tracks:t.mute=t.name!=chosen
    scene.frame_set(frame)
    cam=scene.camera
    cam.location=camera
    cam.rotation_euler=(Vector((0,0,1.03))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.ortho_scale=scale
    scene.render.filepath=os.path.join(OUT,name)
    bpy.ops.render.render(write_still=True)
    assert os.path.getsize(scene.render.filepath)>20000,name
    print("NOVA_RENDER",chosen,scene.render.filepath,os.path.getsize(scene.render.filepath),flush=True)
