#!/usr/bin/env python3
"""Photographic studio renders, with the ACTUAL Blender pose actions applied."""
import bpy,os,sys,math
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=os.path.abspath(argv[0] if argv else "/tmp/kinetic-human")
os.makedirs(out,exist_ok=True)
scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=32
scene.render.resolution_x=1440
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.threads_mode="FIXED"
scene.render.threads=4
scene.view_settings.view_transform='AgX'
try:bpy.context.view_layer.cycles.use_denoising=False
except:pass
rig=bpy.data.objects["KINETIC_HUMAN_RIG"]
for track in rig.animation_data.nla_tracks:track.mute=True
cam=scene.camera
render_list=[
    ("KINETIC-HUMAN-01-Idle.png","Idle_Breathing",20,(2.7,-5.1,2.50),2.53),
    ("KINETIC-HUMAN-02-Walk.png","Walk_Loop",12,(3.15,-5.0,2.37),2.57),
    ("KINETIC-HUMAN-03-Run.png","Run_Loop",10,(3.18,-5.0,2.41),2.57),
    ("KINETIC-HUMAN-04-Punch.png","Punch_Right_Jab",26,(2.7,-4.65,2.45),2.45),
]
for filename,action,frame,position,orthoscale in render_list:
    rig.animation_data.action=bpy.data.actions[action]
    scene.frame_set(frame)
    cam.location=position
    cam.rotation_euler=(Vector((0,0,1.02))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.ortho_scale=orthoscale
    scene.render.filepath=os.path.join(out,filename)
    bpy.ops.render.render(write_still=True)
    print("HUMAN_RENDER",filename,os.stat(scene.render.filepath).st_size,flush=True)
print("HUMAN_RENDERING_COMPLETED")
