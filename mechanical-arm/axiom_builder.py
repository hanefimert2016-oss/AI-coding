#!/usr/bin/env python3
"""AXIOM-6 | high-detail industrial robotic arm.
All meshes are CREATED IN BLENDER via bpy, and --live builds the arm piece by
piece inside the actual Blender GUI while ffmpeg captures the desktop.
No game engine, no image AI, no pre-existing model files.
"""
import bpy, math, os, sys
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT=os.path.abspath(argv[0]) if argv else "/tmp/axiom6"
LIVE="--live" in argv
os.makedirs(OUT,exist_ok=True)
ARM=[]
STUDIO=[]
MAT={}

def mat(name, rgb, metal=0.0, rough=.4, emission=0):
    material=bpy.data.materials.get(name)
    if material: return material
    material=bpy.data.materials.new(name)
    material.diffuse_color=(*rgb,1)
    material.use_nodes=True
    bsdf=material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*rgb,1)
    bsdf.inputs["Metallic"].default_value=metal
    bsdf.inputs["Roughness"].default_value=rough
    if emission:
        bsdf.inputs["Emission Color"].default_value=(*rgb,1)
        bsdf.inputs["Emission Strength"].default_value=emission
    return material

def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.engine='BLENDER_WORKBENCH'
    MAT.update({
        "white":mat("Ceramic alloy | porcelain white",(.72,.82,.88),.63,.24),
        "carbon":mat("Forged carbon | charcoal graphite",(.025,.037,.065),.35,.35),
        "gunmetal":mat("Titanium | satin gunmetal",(.13,.19,.25),.88,.25),
        "chrome":mat("Machined chrome | polished edges",(.48,.64,.74),.93,.18),
        "dark":mat("Anodized titanium | black",(.052,.078,.105),.80,.29),
        "gold":mat("Axial coupling | champagne bronze",(.76,.45,.16),.78,.22),
        "orange":mat("Safety marking | burnt amber",(.98,.36,.095),.35,.35),
        "cyan":mat("Live diagnostic light | neon ice",(.025,.83,1),.1,.35,3.2),
        "screen":mat("Status display | teal glass",(.015,.16,.21),.4,.18,1.4),
        "steel":mat("Hydraulic piston | brushed steel",(.48,.52,.55),.9,.21),
        "rubber":mat("Rubber cable sheathing",(.014,.022,.035),.12,.88),
        "yellow":mat("Service stencil | ivory yellow",(.98,.79,.35),.18,.45),
        "floor":mat("Product studio floor",(.035,.044,.064),.18,.48),
    })
    scene=bpy.context.scene
    scene.world.color=(.08,.08,.08)
    camera_data=bpy.data.cameras.new("85mm product hero lens")
    camera=bpy.data.objects.new("CAMERA | isometric engineering view",camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location=(3.0,-4.0,2.60)
    direction=Vector((.38,0,.89))-camera.location
    camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    camera_data.type='ORTHO'
    camera_data.ortho_scale=2.94
    scene.camera=camera
    STUDIO.append(camera)
    for name,loc,power,rgb,size in [
        ("STUDIO | broad cool softbox",(-3,-4,5),2400,(.48,.77,1),4.0),
        ("STUDIO | warm rim",(3,3,4.8),2600,(1,.61,.37),3.5),
        ("STUDIO | upper key",(1.6,-1.1,6),2000,(1,1,1),3.2)
    ]:
        data=bpy.data.lights.new(name,"AREA")
        data.energy=power
        data.color=rgb
        data.shape="DISK"
        data.size=size
        o=bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(o)
        o.location=loc
        STUDIO.append(o)
    cube("STUDIO FLOOR", (0,0,-.075), (100,100,.14),MAT["floor"],collection=STUDIO,bevel=0)
    if LIVE:
        for area in bpy.context.screen.areas:
            if area.type=="VIEW_3D":
                space=area.spaces.active
                space.region_3d.view_perspective='CAMERA'
                space.shading.type='SOLID'
                space.shading.color_type='MATERIAL'
                space.shading.show_cavity=True
                space.shading.cavity_type='BOTH'
                space.shading.curvature_ridge_factor=1.5
                space.shading.curvature_valley_factor=1.1
                space.overlay.show_floor=False
                space.overlay.show_axis_x=False
                space.overlay.show_axis_y=False
    print("AXIOM_PHASE 00 SETUP",flush=True)

def owned(o,name,material,collection=ARM,bevel=0.0,segments=3):
    o.name=name
    if o.type=='MESH':
        o.data.materials.clear()
        o.data.materials.append(material)
        if bevel:
            mod=o.modifiers.new("CNC rounded machined edges","BEVEL")
            mod.width=bevel
            mod.segments=segments
            mod.affect='EDGES' if hasattr(mod,'affect') else None  # version compatibility below
            mod.loop_slide=True
            o.modifiers.new("Face normals for precise highlights","WEIGHTED_NORMAL")
    collection.append(o)
    return o

def cube(name,where,dims,material,collection=ARM,bevel=.02,rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=where)
    o=bpy.context.object
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rot: o.rotation_euler=rot
    return owned(o,name,material,collection,bevel)

def cyl(name,where,radius,depth,material,collection=ARM,verts=48,bevel=.015,rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth, location=where)
    o=bpy.context.object
    if rot:o.rotation_euler=rot
    return owned(o,name,material,collection,bevel)

def torus(name,where,major,minor,material,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,
        major_radius=major,minor_radius=minor,location=where,rotation=rot)
    return owned(bpy.context.object,name,material)

def sphere(name,where,dims,material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=where)
    o=bpy.context.object
    o.scale=dims
    return owned(o,name,material)

def rod(name,a,b,radius,material,verts=20):
    start=Vector(a)
    end=Vector(b)
    vec=end-start
    ob=cyl(name,(start+end)*.5,radius,vec.length,material,verts=verts,bevel=.002)
    ob.rotation_euler=vec.to_track_quat('Z','Y').to_euler()
    return ob

def beam(name,a,b,width,depth,material,bevel=.035):
    start=Vector(a)
    end=Vector(b)
    vec=end-start
    ob=cube(name,(start+end)*.5,(width,depth,vec.length),material,bevel=bevel)
    ob.rotation_euler=vec.to_track_quat('Z','Y').to_euler()
    return ob

def bolt(name,point,axis="Y",size=.015):
    eul=(0,0,0) if axis=="Z" else ((math.pi/2,0,0) if axis=="Y" else (0,math.pi/2,0))
    cyl(name+" | machine bolt",point,size,.011,MAT["chrome"],verts=12,bevel=.003,rot=eul)
    # hex inset
    cyl(name+" | socket",Vector(point)+Vector((0,-.006,0)) if axis=="Y" else point,size*.45,.013,MAT["dark"],verts=6,bevel=.001,rot=eul)

def label_text(text,where,size=.025,rot=(math.pi/2,0,0),color="yellow"):
    curve=bpy.data.curves.new("LASER ETCH / "+text,"FONT")
    curve.body=text
    curve.size=size
    curve.align_x="CENTER"
    curve.extrude=.0005
    o=bpy.data.objects.new("LASER MARK | "+text,curve)
    bpy.context.collection.objects.link(o)
    o.location=where
    o.rotation_euler=rot
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj=bpy.context.view_layer.objects.active
    obj.data.materials.append(MAT[color])
    ARM.append(obj)
    return obj

def cable(name,points,matname="rubber",radius=.009):
    cv=bpy.data.curves.new(name,'CURVE')
    cv.dimensions='3D'
    cv.resolution_u=12
    cv.bevel_depth=radius
    cv.bevel_resolution=3
    spline=cv.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for bp,pos in zip(spline.bezier_points,points):
        bp.co=pos
        bp.handle_left_type='AUTO'
        bp.handle_right_type='AUTO'
    ob=bpy.data.objects.new(name,cv)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ob=bpy.context.view_layer.objects.active
    ob.data.materials.append(MAT[matname])
    ARM.append(ob)

def phase_base():
    cyl("01 | heavyweight anti-vibration base",(.0,0,.075),.240,.145,MAT["dark"],verts=96,bevel=.022)
    cyl("01 | base chrome chamfer",(.0,0,.145),.229,.018,MAT["chrome"],verts=96)
    cyl("01 | yaw index dial",(.0,0,.183),.197,.063,MAT["gunmetal"],verts=96)
    torus("01 | illuminated 360-degree encoder",(0,0,.214),.18,.008,MAT["cyan"])
    cyl("01 | shoulder riser",(0,0,.264),.132,.115,MAT["white"],verts=64,bevel=.025)
    for i in range(8):
        a=math.tau*i/8
        p=(math.cos(a)*.205,math.sin(a)*.205,.156)
        bolt("01 | base anchor %02d"%i,p,axis="Z",size=.012)
    for i in range(4):
        a=math.tau*i/4
        sphere("01 | anti-slip rubber pad %d"%i,(math.cos(a)*.188,math.sin(a)*.188,.017),(.032,.032,.014),MAT["rubber"])
    cube("01 | service USB panel",(.0,-.130,.265),(.133,.024,.067),MAT["carbon"],bevel=.009)
    cube("01 | service socket LED",(.044,-.146,.272),(.012,.006,.014),MAT["cyan"],bevel=.003)
    label_text("AXIOM / 6",(.0,-.252,.077),.023)
    print("AXIOM_PHASE 01 BASE",len(ARM),flush=True)

def phase_shoulder():
    for y in (-.102,.102):
        cube("02 | cast shoulder yoke",(.035,y,.443),(.172,.053,.292),MAT["white"],bevel=.027)
        cyl("02 | shoulder bearing",(.090,y*1.24,.495),.080,.030,MAT["gunmetal"],
            rot=(math.pi/2,0,0),verts=64)
        torus("02 | shoulder bronze seal",(.090,y*1.47,.495),.063,.010,MAT["gold"],rot=(math.pi/2,0,0))
        for i in range(6):
            a=math.tau*i/6
            bolt("02 | shoulder bolt %d"%i,(.090+math.cos(a)*.048,y*1.58,.495+math.sin(a)*.048),size=.006)
    cyl("02 | heavy joint shaft",(.090,0,.495),.062,.290,MAT["steel"],
        rot=(math.pi/2,0,0),verts=64)
    cube("02 | shoulder rear cover",(-.068,-.09,.464),(.075,.12,.20),MAT["carbon"],bevel=.018)
    print("AXIOM_PHASE 02 SHOULDER",len(ARM),flush=True)

def phase_upper():
    a=(.084,0,.52);b=(.342,0,1.17)
    beam("03 | tapered ceramic upper arm chassis",a,b,.158,.208,MAT["white"],.047)
    beam("03 | recessed carbon fiber dorsal keel",(.077,-.123,.60),(.33,-.123,1.112),.116,.027,MAT["carbon"],.018)
    beam("03 | polished support spar",(.073,.123,.58),(.32,.123,1.12),.052,.025,MAT["chrome"],.012)
    beam("03 | raised center armor spine",(.09,-.146,.67),(.315,-.146,1.105),.040,.014,MAT["gunmetal"],.006)
    beam("03 | optical trace left",(.053,-.150,.695),(.29,-.150,1.113),.009,.006,MAT["cyan"],.002)
    for i in range(5):
        z=.664+i*.085
        x=.13+(z-.664)*.39
        cube("03 | upper arm ventilation tooth %02d"%i,(x,.123,z),(.082,.010,.017),MAT["carbon"],bevel=.004)
    label_text("SERVO / R 06",(.21,-.161,.899),.019)
    print("AXIOM_PHASE 03 UPPER ARM",len(ARM),flush=True)

def phase_elbow():
    elbow=(.343,0,1.17)
    cyl("04 | elbow rotor main",elbow,.118,.265,MAT["dark"],rot=(math.pi/2,0,0),verts=72)
    for y in (-.151,.151):
        cyl("04 | ceramic joint cover",(.343,y,1.17),.133,.050,MAT["white"],rot=(math.pi/2,0,0),verts=72,bevel=.016)
        cyl("04 | annular gear teeth",(.343,y*1.24,1.17),.095,.016,MAT["gunmetal"],rot=(math.pi/2,0,0),verts=64)
        torus("04 | glowing joint encoder",(.343,y*1.32,1.17),.079,.008,MAT["cyan"],rot=(math.pi/2,0,0))
        cyl("04 | micro gear boss",(.343,y*1.36,1.17),.038,.018,MAT["gold"],rot=(math.pi/2,0,0))
        for i in range(8):
            angle=i*math.tau/8
            bolt("04 | elbow M4 clamp %d"%i,(.343+math.cos(angle)*.111,y*1.40,1.17+math.sin(angle)*.111),size=.005)
    print("AXIOM_PHASE 04 ELBOW JOINT",len(ARM),flush=True)

def phase_forearm():
    beam("05 | forged forearm inner chassis",(.37,0,1.18),(.79,0,1.57),.18,.15,MAT["gunmetal"],.04)
    beam("05 | upper smart armor",(.405,-.083,1.235),(.75,-.083,1.565),.156,.053,MAT["white"],.025)
    beam("05 | lower smart armor",(.405,.080,1.21),(.75,.080,1.555),.154,.052,MAT["white"],.025)
    beam("05 | central exposed actuator groove",(.42,-.119,1.26),(.75,-.119,1.56),.066,.018,MAT["carbon"],.008)
    beam("05 | high voltage tracer",(.42,-.130,1.27),(.743,-.130,1.55),.013,.005,MAT["cyan"],.002)
    for i in range(5):
        z=1.315+i*.054;x=.503+i*.052
        cube("05 | titanium heat fin %02d"%i,(x,.113,z),(.06,.024,.011),MAT["chrome"],bevel=.003)
    label_text("AXIS 03 / 250 Nm",(.63,-.151,1.471),.014)
    print("AXIOM_PHASE 05 FOREARM",len(ARM),flush=True)

def phase_wrist():
    center=(.807,0,1.58)
    cyl("06 | wrist roll coupling",center,.071,.195,MAT["carbon"],rot=(math.pi/2,0,0),verts=64)
    for y in (-.105,.105):
        cyl("06 | universal wrist endcap",(.806,y,1.58),.092,.032,MAT["chrome"],rot=(math.pi/2,0,0),verts=64)
        torus("06 | wrist positional encoder",(.806,y*1.25,1.58),.075,.008,MAT["gold"],rot=(math.pi/2,0,0))
    beam("06 | gripper adapter",(.843,0,1.59),(1.000,0,1.55),.086,.103,MAT["gunmetal"],.018)
    cube("06 | tool release mechanism",(1.00,0,1.55),(.080,.170,.137),MAT["white"],bevel=.015)
    for y in (-.085,.085):
        cube("06 | tool lock tab",(1.035,y,1.562),(.041,.024,.06),MAT["gold"],bevel=.008)
    print("AXIOM_PHASE 06 UNIVERSAL WRIST",len(ARM),flush=True)

def phase_gripper():
    cyl("07 | tool changer rotary clasp",(1.068,0,1.55),.075,.116,MAT["gunmetal"],verts=64,rot=(0,math.pi/2,0))
    cyl("07 | gripper palm motor",(1.152,0,1.55),.098,.110,MAT["white"],verts=64,rot=(0,math.pi/2,0))
    for idx,offset in enumerate((-.096,0,.096)):
        z=1.55 + (.037 if idx==1 else -.035)
        base=(1.195,offset,z)
        tip=(1.334,offset*1.20,z-.042)
        tip2=(1.416,offset*1.13,z-.108)
        beam("07 | fingertip %d upper actuator"%idx,base,tip,.055,.045,MAT["white"],.013)
        sphere("07 | finger joint %d"%idx,tip,(.032,.035,.035),MAT["chrome"])
        beam("07 | fingertip %d distal"%idx,tip,tip2,.047,.038,MAT["gunmetal"],.012)
        cube("07 | fingertip silicone pad %d"%idx,
            (tip2[0]+.017,tip2[1],tip2[2]-.012),(.04,.051,.057),MAT["rubber"],bevel=.010)
        cube("07 | tactile optical sensor %d"%idx,
            (tip2[0]+.040,tip2[1],tip2[2]-.013),(.009,.033,.012),MAT["cyan"],bevel=.003)
    print("AXIOM_PHASE 07 PRECISION THREE-FINGER TOOL",len(ARM),flush=True)

def phase_hydraulics():
    for y in (-.165,.165):
        rod("08 | primary hydraulic reservoir",(.01,y,.38),(.20,y,.795),.034,MAT["gunmetal"])
        rod("08 | primary chrome ram",(.20,y,.795),(.299,y,.99),.019,MAT["chrome"])
        for pt in ((.01,y,.38),(.20,y,.795)):
            sphere("08 | metal spherical rod bearing",pt,(.043,.043,.043),MAT["gold"])
        rod("08 | secondary actuator reservoir",(.328,y*.88,1.157),(.506,y*.88,1.325),.028,MAT["gunmetal"])
        rod("08 | secondary polished rod",(.506,y*.88,1.325),(.615,y*.88,1.414),.014,MAT["chrome"])
        for pt in ((.328,y*.88,1.157),(.506,y*.88,1.325)):
            sphere("08 | secondary ball end",pt,(.035,.035,.035),MAT["gold"])
    print("AXIOM_PHASE 08 DUAL HYDRAULIC ACTUATION",len(ARM),flush=True)

def phase_cabling():
    for n in range(4):
        y=.125+n*.021
        cable("09 | servo CANBUS braided line %d"%n,[
            (-.049,y,.260),
            (-.11,y+.012,.46),
            (.010,y+.025,.835),
            (.260,y+.031,1.17),
            (.40,y+.017,1.345),
            (.79,y*.58,1.64)],radius=.008 if n%2==0 else .006)
        for z,x in ((.44,-.104),(.865,.026),(1.29,.32)):
            torus("09 | protective cable clamp", (x,y+.007,z),.018,.004,MAT["gold"],rot=(0,math.pi/2,0))
    for n in range(8):
        a=n*math.tau/8
        bx=math.cos(a)*.142;by=math.sin(a)*.142
        cube("09 | base tooling marker", (bx,by,.182),(.012,.022,.012),MAT["gold"],bevel=.002)
    print("AXIOM_PHASE 09 BRAIDED HARNESS + ENCODERS",len(ARM),flush=True)

def phase_finishing():
    for i in range(5):
        x=.388+i*.063
        sphere("10 | optical machine status LED %02d"%i,(x,-.155,1.28+i*.058),
            (.009,.006,.009),MAT["cyan"])
    for z in (.703,.761,.820,1.432):
        beam("10 | ceramic panel inset",(.12,-.151,z),(.174,-.151,z+.032),.028,.008,MAT["gold"],.004)
    label_text("6 AXIS / INDUSTRIAL",(.02,-.143,.293),.011)
    print("AXIOM_PHASE 10 ENGINEERED SURFACE FINISH",len(ARM),flush=True)

PHASES=[
    phase_base,phase_shoulder,phase_upper,phase_elbow,phase_forearm,
    phase_wrist,phase_gripper,phase_hydraulics,phase_cabling,phase_finishing
]

def save_final():
    # Exclude floor, lamps and studio camera from exported mechanical model.
    bpy.ops.object.select_all(action='DESELECT')
    for o in ARM: o.select_set(True)
    bpy.context.view_layer.objects.active=ARM[0]
    fn=os.path.join(OUT,"AXIOM-6-Industrial-Robotic-Arm.blend")
    bpy.ops.wm.save_as_mainfile(filepath=fn)
    print("BLEND_FILE",fn,os.stat(fn).st_size,flush=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT,"AXIOM-6-Industrial-Robotic-Arm.glb"),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT"
    )
    glb=os.path.join(OUT,"AXIOM-6-Industrial-Robotic-Arm.glb")
    print("GLB_FILE",glb,os.stat(glb).st_size,flush=True)
    print("AXIOM_OBJECT_COUNT",len(ARM),flush=True)
    print("AXIOM_COMPLETED",flush=True)

setup()
if LIVE:
    state={"i":0}
    def step():
        n=state["i"]
        if n<len(PHASES):
            PHASES[n]()
            state["i"]=n+1
            for a in bpy.context.screen.areas:
                a.tag_redraw()
            return 3.3
        save_final()
        return None
    bpy.app.timers.register(step,first_interval=3.0)
    print("AXIOM_LIVE_GUI_MODELING_STARTED",flush=True)
else:
    for phase in PHASES: phase()
    save_final()
