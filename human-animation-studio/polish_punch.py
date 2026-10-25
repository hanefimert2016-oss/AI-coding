#!/usr/bin/env python3
"""Refine right boxing jab using exact rest-bone orientation math.

Unlike hand-tuned global Euler angles, bone frame conversions ensure both
the upper arm and forearm point forward in the correct space, visibly extending
the right hand toward the viewer. Preserves all other skeletal animations.
"""
import bpy,math,os,sys,json,struct
from mathutils import Vector
out=os.path.abspath(sys.argv[sys.argv.index("--")+1])
rig=bpy.data.objects["KINETIC_HUMAN_RIG"]
arm=rig.data
act=bpy.data.actions["Punch_Right_Jab"]
rig.animation_data.action=act
for track in rig.animation_data.nla_tracks:track.mute=True

upper=rig.pose.bones["UpperArm.R"]
fore=rig.pose.bones["Forearm.R"]
r_chest=rig.pose.bones["Chest"]
r_spine=rig.pose.bones["Spine"]
upper_rest=(upper.bone.tail_local-upper.bone.head_local).normalized()
fore_rest=(fore.bone.tail_local-fore.bone.head_local).normalized()
u_q=upper.bone.matrix_local.to_quaternion()
f_q=fore.bone.matrix_local.to_quaternion()

def interp(a,b,w):
    return a.lerp(b,min(1.0,max(0.0,w))).normalized()

for frame in list(range(1,49,3))+[49]:
    s=(frame-1)/48.0
    wind=min(1.0,max(0.0,(s-.11)/.22))
    release=min(1.0,max(0.0,(s-.67)/.17))
    hit=wind*(1.0-release)
    # Rest upper arm points down/outside; desired points forward
    # (negative Y) with an anatomically plausible shoulder position.
    aim_upper=interp(upper_rest,Vector((.03,-.98,-.12)).normalized(),hit)
    q_world_upper=upper_rest.rotation_difference(aim_upper)
    delta_upper=u_q.inverted() @ q_world_upper @ u_q
    upper.rotation_mode='XYZ'
    upper.rotation_euler=delta_upper.to_euler('XYZ')
    upper.keyframe_insert(data_path="rotation_euler",frame=frame,group=upper.name)

    # Calculate wrist direction after shoulder rotation in REST parent
    # space, then convert precisely back to forearm's LOCAL axes.
    goal_fore=interp(fore_rest,Vector((.30,-.94,.04)).normalized(),hit)
    target_in_upper_rest=q_world_upper.inverted() @ goal_fore
    f_world_d=fore_rest.rotation_difference(target_in_upper_rest)
    delta_fore=f_q.inverted() @ f_world_d @ f_q
    fore.rotation_mode='XYZ'
    fore.rotation_euler=delta_fore.to_euler('XYZ')
    fore.keyframe_insert(data_path="rotation_euler",frame=frame,group=fore.name)

    # Reduce exaggerated whole-torso tilt in the original action.
    chest=r_chest.rotation_euler.copy()
    chest.z=-.052*hit
    chest.x=.015*hit
    r_chest.rotation_euler=chest
    r_chest.keyframe_insert(data_path="rotation_euler",frame=frame,group=r_chest.name)
    spine=r_spine.rotation_euler.copy()
    spine.z=-.020*hit
    r_spine.rotation_euler=spine
    r_spine.keyframe_insert(data_path="rotation_euler",frame=frame,group=r_spine.name)

for fc in act.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation="BEZIER"

scene=bpy.context.scene
scene.frame_set(26)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,"KINETIC-HUMAN-Rigged-Animated.blend"))
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for obj in bpy.data.objects:
    if obj.type=="MESH" and any(mod.type=="ARMATURE" and mod.object==rig for mod in obj.modifiers):
        obj.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=os.path.join(out,"KINETIC-HUMAN-Rigged-Animated.glb")
options={"filepath":glb,"export_format":"GLB","use_selection":True,
         "export_materials":"EXPORT","export_animations":True,
         "export_nla_strips":False}
bpy.ops.export_scene.gltf(**options)
b=open(glb,"rb").read();n=struct.unpack_from('<I',b,12)[0]
data=json.loads(b[20:20+n])
if len(data.get('animations',[]))<4:
    for track in rig.animation_data.nla_tracks:track.mute=False
    rig.animation_data.action=None
    bpy.ops.export_scene.gltf(**{**options,"export_nla_strips":True})
    b=open(glb,"rb").read();n=struct.unpack_from('<I',b,12)[0]
    data=json.loads(b[20:20+n])
names=[a.get('name','') for a in data.get("animations",[])]
assert len(data.get("skins",[]))>=1
for name in ("Walk","Run","Punch","Idle"):
    assert any(name.lower() in anim.lower() for anim in names), names
assert (os.path.getsize(glb)>50000)
print("REVISED_JAB_SUCCESS",names,flush=True)
print("REVISED_SHOULDER_ROTATION",list(upper.rotation_euler),flush=True)
print("REVISED_FOREARM_ROTATION",list(fore.rotation_euler),flush=True)
