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
    camera_data.ortho_scale=2.55
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
        try:
            bpy.context.preferences.view.show_splash=False
        except Exception: pass
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
                space.overlay.show_extras=False
                space.overlay.show_cursor=False
                space.region_3d.view_camera_zoom=9
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
            if hasattr(mod, 'affect'):
                mod.affect = 'EDGES'
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


# ================= AXIOM-6 PRO / ADVANCED FABRICATION ===================
def machined_shell(name, start, end, sections, material, radial=16):
    """Bespoke lofted polygonal CNC shells, not just stretched cube primitives.
    sections: [(t, width, depth)] along the shell's local longitudinal axis.
    """
    start=Vector(start); end=Vector(end)
    direction=end-start;length=direction.length
    vertices=[]
    for t,width,depth in sections:
        for j in range(radial):
            theta=2.0*math.pi*j/radial
            # Squircle profile produces machined flattened sides / gently radiused corners.
            cosv=math.cos(theta);sinv=math.sin(theta)
            u=math.copysign(abs(cosv)**0.70,cosv)
            v=math.copysign(abs(sinv)**0.70,sinv)
            vertices.append((u*width/2.0,v*depth/2.0,(t-.5)*length))
    faces=[]
    faces.append(tuple(reversed(range(radial))))
    for i in range(len(sections)-1):
        for j in range(radial):
            a=i*radial+j
            b=i*radial+(j+1)%radial
            faces.append((a,b,b+radial,a+radial))
    last=(len(sections)-1)*radial
    faces.append(tuple(last+j for j in range(radial)))
    mesh=bpy.data.meshes.new(name+" CAD quad shell")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.location=(start+end)*.5
    obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
    return owned(obj,name,material,bevel=.004,segments=3)

def gearwheel(name,center,radius,teeth,axis="Y",matname="gunmetal"):
    """Assembled ring gear with machined individual teeth."""
    cx,cy,cz=center
    if axis=="Y":
        orient=(math.pi/2,0,0)
    elif axis=="X":
        orient=(0,math.pi/2,0)
    else:
        orient=(0,0,0)
    cyl(name+" / annular gear hub",center,radius*.86,.044,MAT[matname],
        rot=orient,verts=72,bevel=.006)
    torus(name+" / pitch ring",center,radius*.82,.012,MAT["chrome"],rot=orient)
    for j in range(teeth):
        phi=j*math.tau/teeth
        if axis=="Y":
            where=(cx+math.cos(phi)*radius,cy,cz+math.sin(phi)*radius)
            rotation=(0,-phi,0)
            dims=(.022,.051,.018)
        elif axis=="X":
            where=(cx,cy+math.cos(phi)*radius,cz+math.sin(phi)*radius)
            rotation=(phi,0,0)
            dims=(.051,.018,.022)
        else:
            where=(cx+math.cos(phi)*radius,cy+math.sin(phi)*radius,cz)
            rotation=(0,0,phi)
            dims=(.022,.018,.051)
        cube(name+" / involute tooth %02d"%j,where,dims,MAT["steel"],
             bevel=.002,rot=rotation)

def phase_pro_shells():
    machined_shell("11 / bespoke upper ceramic exoshell",
                   (.105,-.042,.64),(.303,-.044,1.075),
                   [(0,.12,.23),(.10,.205,.29),(.45,.22,.30),(.85,.18,.265),(1,.115,.17)],
                   MAT["white"],radial=24)
    machined_shell("11 / CNC lower forearm fairing",
                   (.444,-.03,1.27),(.739,-.028,1.526),
                   [(0,.095,.18),(.18,.205,.260),(.68,.21,.26),(1,.105,.17)],
                   MAT["white"],radial=24)
    machined_shell("11 / rear structural carbon inset",
                   (.12,-.176,.677),(.281,-.176,1.049),
                   [(0,.078,.01),(.18,.132,.014),(.72,.116,.012),(1,.071,.01)],
                   MAT["carbon"],radial=16)
    machined_shell("11 / rear forearm carbon inset",
                   (.470,-.145,1.291),(.715,-.145,1.51),
                   [(0,.06,.01),(.25,.125,.012),(.76,.120,.012),(1,.04,.01)],
                   MAT["carbon"],radial=16)
    for n in range(8):
        t=n/7
        p=(.119+.192*t, -.185, .699+.355*t)
        cube("11 / machined dorsal louvre %02d"%n,p,
             (.058+.014*math.sin(t*math.pi),.016,.014),MAT["gunmetal"],bevel=.003)
        cube("11 / illuminated dorsal track %02d"%n,
             (p[0]+.047,p[1]-.007,p[2]),(.009,.012,.013),
             MAT["cyan"],bevel=.002)
    for n in range(6):
        x=.48+n*.041; z=1.32+n*.038
        cube("11 / honeycomb forearm exhaust fin %02d"%n,
             (x,.155,z),(.059,.024,.020),MAT["carbon"],bevel=.004)
    print("AXIOM_PHASE 11 CUSTOM CNC SHELLS",len(ARM),flush=True)

def phase_pro_gearboxes():
    gearwheel("12 / shoulder internal precision drive",(.090,-.159,.495),.065,24,"Y")
    gearwheel("12 / elbow planetary ring",(.343,-.207,1.17),.099,32,"Y")
    gearwheel("12 / wrist indexed roll",(.806,-.146,1.58),.060,20,"Y")
    for n in range(12):
        angle=math.tau*n/12
        position=(.090+math.cos(angle)*.077,-.226,.495+math.sin(angle)*.077)
        bolt("12 / shoulder inner ring M3 %02d"%n,position,size=.0035)
    for n in range(12):
        angle=math.tau*n/12
        position=(.343+math.cos(angle)*.121,-.226,1.17+math.sin(angle)*.121)
        bolt("12 / elbow inner ring M3 %02d"%n,position,size=.0035)
    print("AXIOM_PHASE 12 PLANETARY GEARTRAINS",len(ARM),flush=True)

def phase_pro_actuators():
    for side in (-1,1):
        y=side*.189
        rod("13 / servo hydraulic triple-stage barrel",(.030,y,.48),(.21,y,.86),.041,MAT["carbon"])
        rod("13 / servo inner telescopic actuator",(.195,y,.827),(.275,y,1.026),.017,MAT["chrome"])
        for p in ((.05,y,.50),(.22,y,.88)):
            sphere("13 / spherical hydraulic ball pivot",p,(.027,.027,.027),MAT["gold"])
        for n in range(4):
            t=n/3
            pos=(.043+.17*t,y,.51+.34*t)
            torus("13 / piston circumferential wear seal %02d"%n,pos,.038,.005,MAT["gold"],
                  rot=(0,0,-.42))
        cable("13 / high pressure hose port",[
            (-.054,y,.32),(-.12,y,.50),(.027,y,.73),(.215,y,1.0)],
            matname="rubber",radius=.010)
        cable("13 / blue coolant return line",[
            (-.06,y*.70,.29),(-.10,y*.80,.58),(.10,y*.75,.91),(.31,y*.90,1.145)],
            matname="cyan",radius=.004)
        for j in range(7):
            t=j/6
            px=.113+.25*t;pz=.76+.40*t
            cube("13 / hydraulic heat exchanger tooth %02d"%j,
                (px,y*.84,pz),(.038,.025,.015),MAT["gunmetal"],bevel=.003)
    print("AXIOM_PHASE 13 HYDRAULIC ACTUATORS",len(ARM),flush=True)

def phase_pro_tooling():
    for idx,offset in enumerate((-.096,0,.096)):
        for n in range(5):
            x=1.335+n*.017
            z=1.49-.018*n
            cube("14 / fingertip micro-knurl %d-%d"%(idx,n),
                (x,offset*1.12,z),(.012,.037,.012),MAT["rubber"],bevel=.002)
        for n in range(4):
            x=1.21+n*.032
            sphere("14 / fingertip strain sensor %d-%d"%(idx,n),
                (x,offset*1.08,1.563-n*.01),
                (.008,.010,.006),MAT["cyan"])
        bolt("14 / end effector mounting bolt %d"%idx,
            (1.179,offset,1.55),axis="X",size=.008)
    for n in range(12):
        a=n*math.tau/12
        px=.138*math.cos(a);py=.138*math.sin(a)
        cyl("14 / yaw laser index stud %02d"%n,(px,py,.210),.007,.008,MAT["orange"],verts=16,bevel=.002)
    for n in range(4):
        cable("14 / wired finger strain gauges %02d"%n,
              [(.79,n*.038-.06,1.58),(.94,n*.039-.06,1.64),
               (1.07,n*.041-.07,1.61),(1.21,n*.041-.07,1.59)],
              radius=.003,matname="gold" if n%2==0 else "rubber")
    print("AXIOM_PHASE 14 MICRO PRECISION GRIPPER",len(ARM),flush=True)

def phase_pro_identity():
    for i in range(6):
        h=.768+i*.055
        x=.160+i*.021
        bolt("15 / upper chassis captive fastener %d"%i,(x,-.208,h),size=.006)
        cube("15 / brushed CNC edge highlight %d"%i,(x+.022,-.202,h),
             (.025,.007,.003),MAT["chrome"],bevel=.001)
    for i in range(8):
        x=.478+i*.03; z=1.300+i*.026
        bolt("15 / lower chassis captive fastener %d"%i,
             (x,-.169,z),size=.004)
    for i in range(10):
        a=i*math.tau/10
        cube("15 / base radial encoder tick %02d"%i,
             (.180*math.cos(a),.180*math.sin(a),.217),
             (.009,.024,.006),MAT["orange"],bevel=.002,rot=(0,0,a))
    label_text("AXIOM - 6 PRO",(.075,-.207,.87),.015,color="orange")
    label_text("SERVO / INDUSTRIAL",(.53,-.177,1.394),.009,color="yellow")
    print("AXIOM_PHASE 15 DETAIL SURFACE ENGINEERING",len(ARM),flush=True)

PHASES=[
    phase_base,phase_shoulder,phase_upper,phase_elbow,phase_forearm,
    phase_wrist,phase_gripper,phase_hydraulics,phase_cabling,phase_finishing,
    phase_pro_shells,phase_pro_gearboxes,phase_pro_actuators,phase_pro_tooling,phase_pro_identity
]

def save_final():
    # Exclude floor, lamps and studio camera from exported mechanical model.
    bpy.ops.object.select_all(action='DESELECT')
    for o in ARM: o.select_set(True)
    bpy.context.view_layer.objects.active=ARM[0]
    fn=os.path.join(OUT,"AXIOM-6-PRO-Industrial-Robotic-Arm.blend")
    bpy.ops.wm.save_as_mainfile(filepath=fn)
    print("BLEND_FILE",fn,os.stat(fn).st_size,flush=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT,"AXIOM-6-PRO-Industrial-Robotic-Arm.glb"),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT"
    )
    glb=os.path.join(OUT,"AXIOM-6-PRO-Industrial-Robotic-Arm.glb")
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
            # Visible status in the captured Blender screen and console.
            try:
                with open(os.path.join(OUT,"current-stage.txt"),"w") as stage:
                    stage.write("STEP %02d / %02d    %s" % (n+1,len(PHASES),PHASES[n].__name__.replace("phase_","").replace("_"," ").upper()))
            except OSError: pass
            bpy.context.view_layer.update()
            for a in bpy.context.screen.areas:
                a.tag_redraw()
            return 4.0
        save_final()
        return None
    bpy.app.timers.register(step,first_interval=11.0)
    print("AXIOM_LIVE_GUI_MODELING_STARTED",flush=True)
else:
    for phase in PHASES: phase()
    save_final()
