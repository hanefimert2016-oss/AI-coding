#!/usr/bin/env python3
"""Render genuine final rig poses using Blender; render 96 animation
sample frames for an animation demonstration mp4. No substitute media."""
import bpy, os, sys, math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=os.path.abspath(argv[0]) if argv else "/tmp/aether"
os.makedirs(out,exist_ok=True)
arm=bpy.data.objects.get("AETHER_01_DEFORM_RIG")
assert arm and arm.type=="ARMATURE"
assert len(arm.data.bones)>=20
actions={a.name:a for a in bpy.data.actions}
names=("Idle","Walk","Run","Punch")
assert all(x in actions for x in names),list(actions)
if not arm.animation_data:arm.animation_data_create()
for track in arm.animation_data.nla_tracks:track.mute=True
scene=bpy.context.scene
cam=scene.camera
assert cam
scene.render.image_settings.file_format="PNG"
scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.view_settings.view_transform="Standard"
# Scene materials, studio lighting and real skinned geometry are preserved.
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=24
try:bpy.context.view_layer.cycles.use_denoising=False
except Exception:pass
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.render.resolution_x=1440
scene.render.resolution_y=810
views=[
    ("Idle",1,"01-AETHER-Human-Neutral.png",(3.3,-5.9,2.8),Vector((0,0,.98)),2.55),
    ("Walk",15,"02-AETHER-Walking.png",(3.5,-5.6,2.6),Vector((0,0,1.00)),2.6),
    ("Run",11,"03-AETHER-Running.png",(3.5,-5.7,2.65),Vector((0,0,1.0)),2.65),
    ("Punch",21,"04-AETHER-Punching.png",(3.4,-5.6,2.60),Vector((0,0,1.04)),2.65),
    ("Idle",1,"05-AETHER-Portrait-Closeup.png",(1.3,-3.6,2.07),Vector((0,0,1.72)),.88),
]
for action_name,frame,filename,loc,target,scale in views:
    arm.animation_data.action=actions[action_name]
    scene.frame_set(frame)
    cam.location=loc
    cam.rotation_euler=(target-Vector(cam.location)).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale
    path=os.path.join(out,filename)
    scene.render.filepath=path
    bpy.ops.render.render(write_still=True)
    assert os.path.getsize(path)>12000
    print("AETHER_RENDER",filename,os.path.getsize(path),flush=True)
# Motion studio: manually sample true Blender armature actions to PNG frames.
scene.render.engine="BLENDER_WORKBENCH"
scene.display.shading.light="STUDIO"
scene.display.shading.color_type="MATERIAL"
scene.display.shading.show_cavity=True
scene.render.resolution_x=960
scene.render.resolution_y=540
cam.location=(3.2,-5.8,2.6)
cam.rotation_euler=(Vector((0,0,.97))-Vector(cam.location)).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=2.7
framedir=os.path.join(out,"sample_frames")
os.makedirs(framedir,exist_ok=True)
counter=0
for action_name in names:
    action=actions[action_name]
    arm.animation_data.action=action
    for frameidx in range(24):
        in_frame=int(1+frameidx*((37 if action_name in ("Run","Punch") else 49)-2)/23)
        scene.frame_set(in_frame)
        scene.render.filepath=os.path.join(framedir,"frame-%04d.png"%counter)
        bpy.ops.render.render(write_still=True)
        counter+=1
    print("AETHER_MOTION_RENDERED",action_name,24,"frames",flush=True)
print("AETHER_MOTION_FRAMES_TOTAL",counter,flush=True)
