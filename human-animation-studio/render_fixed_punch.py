#!/usr/bin/env python3
"""Render corrected punch action from original armature in Blender Cycles."""
import bpy,os,sys
from mathutils import Vector
out=os.path.abspath(sys.argv[sys.argv.index("--")+1])
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.render.resolution_x=1440
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform="AgX"
try:bpy.context.view_layer.cycles.use_denoising=False
except Exception:pass
rig=bpy.data.objects["KINETIC_HUMAN_RIG"]
for t in rig.animation_data.nla_tracks:t.mute=True
rig.animation_data.action=bpy.data.actions["Punch_Right_Jab"]
scene.frame_set(26)
cam=scene.camera
cam.location=(3.1,-6.1,2.65)
cam.rotation_euler=(Vector((0,0,1.02))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=3.76
scene.render.filepath=os.path.join(out,"KINETIC-HUMAN-04-Punch.png")
bpy.ops.render.render(write_still=True)
print("PUNCH_FULL_BODY_REVISED_RENDER",scene.render.filepath,os.stat(scene.render.filepath).st_size)
