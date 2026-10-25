#!/usr/bin/env python3
"""Play actual rig clips in real Blender GUI for honest desktop screen recording."""
import bpy,os,sys,time
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=os.path.abspath(args[0] if args else "/tmp")
scene=bpy.context.scene
rig=bpy.data.objects.get("KINETIC_HUMAN_RIG")
assert rig is not None
for track in rig.animation_data.nla_tracks:track.mute=True
for area in bpy.context.screen.areas:
    if area.type=="VIEW_3D":
        s=area.spaces.active
        s.region_3d.view_perspective='CAMERA'
        s.region_3d.view_camera_zoom=4
        s.shading.type="SOLID"
        s.shading.color_type="MATERIAL"
        s.shading.show_cavity=True
        s.overlay.show_floor=False
        s.overlay.show_axis_x=False
        s.overlay.show_axis_y=False
        s.overlay.show_extras=False
        area.tag_redraw()
start=time.monotonic()
state={"name":None}
def tick():
    elapsed=time.monotonic()-start
    if elapsed>52:return None
    if elapsed<7: name="Idle_Breathing";maxframe=96;phase="IDLE BREATHING"
    elif elapsed<22: name="Walk_Loop";maxframe=48;phase="WALK LOOP"
    elif elapsed<37: name="Run_Loop";maxframe=32;phase="RUN LOOP"
    else: name="Punch_Right_Jab";maxframe=48;phase="RIGHT-HAND PUNCH"
    if state["name"]!=name:
        state["name"]=name
        rig.animation_data.action=bpy.data.actions[name]
        with open(os.path.join(out,"animation-stage.txt"),"w") as f:
            f.write("LIVE ARMATURE PREVIEW / "+phase)
        print("BLENDER_REAL_ACTION_PREVIEW",name,flush=True)
    fps=17
    frame=(int(elapsed*fps)%maxframe)+1
    scene.frame_set(frame)
    return .058
bpy.app.timers.register(tick,first_interval=1.0)
print("ACTUAL_BLEND_RIG_VIDEO_PREVIEW_STARTED",flush=True)
