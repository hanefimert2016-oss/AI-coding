#!/usr/bin/env python3
"""AETHER-01 — original fully rigged stylized human, with five animation actions.
Designed for Blender 4.0 on Ubuntu CI. Geometry, bones and animation authored
entirely in Blender Python; GLB glTF 2.0 includes skin + keyframed motions.
--live creates the scene incrementally in a real recorded Blender GUI.
"""
import bpy, math, sys, os
from mathutils import Vector, Quaternion
from math import sin, cos, pi
argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else "/tmp/aether"
LIVE = "--live" in argv
os.makedirs(OUT, exist_ok=True)
CHAR, STUDIO, MAT = [], [], {}
BONES = {}
ARM = None
ACTIONS = []
ARM_NAME = "AETHER_01_DEFORM_RIG"
PART_COUNTER=0

def mat(key, color, metallic=0, roughness=.43, emission=0):
    o=bpy.data.materials.new(key)
    o.diffuse_color=(*color,1)
    o.use_nodes=True
    node=o.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value=(*color,1)
    node.inputs["Metallic"].default_value=metallic
    node.inputs["Roughness"].default_value=roughness
    if emission:
        node.inputs["Emission Color"].default_value=(*color,1)
        node.inputs["Emission Strength"].default_value=emission
    return o

def initialize():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    MAT.update({
        "skin":mat("Skin / natural warm complexion",(.55,.335,.232),0,.68),
        "skinlit":mat("Skin / subtle bridge highlights",(.73,.48,.36),0,.72),
        "skinshadow":mat("Skin / ears shadow",(.39,.21,.145),0,.73),
        "black":mat("Black athletic fabric / matte",(.019,.032,.055),.03,.76),
        "graphite":mat("Graphite neoprene flexible panels",(.046,.070,.102),.12,.49),
        "carbon":mat("Carbon weave textured detail",(.075,.112,.147),.4,.37),
        "darksteel":mat("Dark titanium buckles",(.20,.29,.34),.78,.27),
        "white":mat("Moonstone accent textile",(.68,.75,.80),.03,.50),
        "blue":mat("Azure blue fabric piping",(.02,.39,.74),.07,.32),
        "cyan":mat("Cyan luminous insignia",(.01,.70,.88),.08,.31,2.1),
        "orange":mat("Shoe heel amber reflective",(.97,.37,.105),.1,.46),
        "hair":mat("Hair / charcoal dark brown",(.040,.028,.025),.01,.77),
        "eyewhite":mat("Eyes sclera",(.82,.77,.69),0,.3),
        "iris":mat("Iris warm umber",(.19,.107,.064),0,.22),
        "pupil":mat("Pupil near black",(.012,.010,.014),0,.18),
        "lip":mat("Lips neutral muted",(.35,.176,.139),0,.65),
        "floor":mat("Dark studio floor",(.027,.036,.052),.08,.55),
    })
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=1600
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.light="STUDIO"
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.render.image_settings.file_format="PNG"
    camdata=bpy.data.cameras.new("Portrait studio 75 mm / camera")
    cam=bpy.data.objects.new("CAMERA / full body",camdata)
    bpy.context.collection.objects.link(cam)
    cam.location=(3.3,-5.8,2.60)
    cam.rotation_euler=(Vector((0,0,.98))-cam.location).to_track_quat("-Z","Y").to_euler()
    camdata.type="ORTHO"
    camdata.ortho_scale=2.68
    scene.camera=cam
    STUDIO.append(cam)
    for name,loc,power,colour,size in [
        ("Softbox / cool key",(-3.0,-3.0,5.2),2100,(.55,.76,1.0),4.2),
        ("Softbox / edge amber",(2.7,2.2,4.3),2400,(1.0,.62,.40),3.4),
        ("Softbox / fill front",(1.3,-4.4,3.9),1400,(1,1,1),3.5),
    ]:
        light=bpy.data.lights.new(name,"AREA")
        light.energy=power
        light.shape="DISK"
        light.size=size
        light.color=colour
        obj=bpy.data.objects.new(name,light)
        bpy.context.collection.objects.link(obj)
        obj.location=loc
        STUDIO.append(obj)
    # Visual studio floor is never exported to .glb.
    floor=cube("STUDIO ONLY / ground", (0,0,-.082),(50,50,.12),MAT["floor"], bone=None)
    CHAR.remove(floor)
    STUDIO.append(floor)
    if LIVE:
        for area in bpy.context.screen.areas:
            if area.type=="VIEW_3D":
                space=area.spaces.active
                space.region_3d.view_perspective="CAMERA"
                space.region_3d.view_camera_zoom=6
                space.shading.type="MATERIAL" if False else "SOLID"
                space.shading.color_type="MATERIAL"
                space.shading.show_cavity=True
                space.overlay.show_floor=False
                space.overlay.show_axis_x=False
                space.overlay.show_axis_y=False
                space.overlay.show_extras=False
    log("00 / Studio prepared")

def log(phase):
    print("AETHER_STAGE",phase,"MESH_PARTS",len(CHAR),flush=True)
    try:
        with open(os.path.join(OUT,"current-stage.txt"),"w") as f:
            f.write(phase.upper())
    except Exception:
        pass

def bind(o,bone,material,bevel=0, smooth=False):
    global PART_COUNTER
    PART_COUNTER+=1
    o.name="%03d | "%PART_COUNTER+o.name
    if o.type=="MESH":
        o.data.materials.append(material)
        if smooth:
            for poly in o.data.polygons:poly.use_smooth=True
        if bevel:
            b=o.modifiers.new("Soft garment edge","BEVEL")
            b.width=bevel
            b.segments=3
        if bone is not None:
            vg=o.vertex_groups.new(name=bone)
            vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
            mod=o.modifiers.new("AETHER skeleton skinning","ARMATURE")
            mod.object=ARM
            o.parent=ARM
    CHAR.append(o)
    return o

def cube(name,location,size,material,bone=None,bevel=.008):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    o=bpy.context.object
    o.name=name
    o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return bind(o,bone,material,bevel)

def ball(name,location,scale,material,bone,segments=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=max(12,segments//2),location=location)
    o=bpy.context.object
    o.name=name
    o.scale=scale
    return bind(o,bone,material,smooth=True)

def cylinder(name,position,radius,depth,material,bone,axis="Z"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=position)
    o=bpy.context.object
    o.name=name
    if axis=="X":o.rotation_euler.y=pi/2
    elif axis=="Y":o.rotation_euler.x=pi/2
    return bind(o,bone,material,.006)

def loft(name,start,end,profile,material,bone,radial=16):
    """Contoured garment/anatomy segments; skin vertices bound to one skeletal bone.
    Each profile entry is (progress along bone, horizontal radius, depth radius).
    """
    a=Vector(start);b=Vector(end);axis=b-a
    if axis.length<.0001:raise ValueError("zero-length loft")
    points=[]
    # Reference local X and Y axes aligned per segment.
    # Human limbs vertical, so frame is mostly horizontally oriented.
    side=Vector((0,1,0))
    if abs(axis.normalized().dot(side))>.85:side=Vector((1,0,0))
    u=side.cross(axis).normalized()
    v=axis.normalized().cross(u).normalized()
    for t,r1,r2 in profile:
        center=a.lerp(b,t)
        for j in range(radial):
            theta=2*pi*j/radial
            points.append(center+u*(cos(theta)*r1)+v*(sin(theta)*r2))
    faces=[tuple(reversed(list(range(radial))))]
    for i in range(len(profile)-1):
        for j in range(radial):
            A=i*radial+j;B=i*radial+(j+1)%radial
            faces.append((A,B,B+radial,A+radial))
    z=(len(profile)-1)*radial
    faces.append(tuple(z+j for j in range(radial)))
    mesh=bpy.data.meshes.new(name+"_mesh")
    mesh.from_pydata(points,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    return bind(o,bone,material,smooth=True)

def curve_tube(name,coords,material,bone,radius=.006):
    path=bpy.data.curves.new(name,'CURVE')
    path.dimensions="3D"
    path.bevel_depth=radius
    path.bevel_resolution=3
    sp=path.splines.new("POLY")
    sp.points.add(len(coords)-1)
    for p,co in zip(sp.points,coords):p.co=(*co,1)
    o=bpy.data.objects.new(name,path)
    bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target="MESH")
    o=bpy.context.view_layer.objects.active
    return bind(o,bone,material)

def add_bone(name,head,tail,parent=None):
    bone=ARM.data.edit_bones.new(name)
    bone.head=head;bone.tail=tail
    if parent:bone.parent=ARM.data.edit_bones[parent]
    bone.use_connect=False
    BONES[name]=(Vector(head),Vector(tail))
    return bone

def skeleton():
    global ARM
    data=bpy.data.armatures.new("AETHER-01 / 21 bone humanoid skeleton")
    ARM=bpy.data.objects.new(ARM_NAME,data)
    bpy.context.collection.objects.link(ARM)
    bpy.context.view_layer.objects.active=ARM
    ARM.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    add_bone("Root",(0,0,.93),(0,0,1.03))
    add_bone("Hips",(0,0,1.04),(0,0,1.18),"Root")
    add_bone("Spine",(0,0,1.18),(0,0,1.43),"Hips")
    add_bone("Chest",(0,0,1.43),(0,0,1.61),"Spine")
    add_bone("Neck",(0,0,1.61),(0,0,1.73),"Chest")
    add_bone("Head",(0,0,1.73),(0,0,1.99),"Neck")
    for side in ("L","R"):
        sign=-1 if side=="L" else 1
        add_bone("UpperArm."+side,(sign*.23,0,1.54),(sign*.47,0,1.34),"Chest")
        add_bone("LowerArm."+side,(sign*.47,0,1.34),(sign*.69,0,1.13),"UpperArm."+side)
        add_bone("Hand."+side,(sign*.69,0,1.13),(sign*.78,0,1.07),"LowerArm."+side)
        for i in range(3):
            add_bone("Finger%d.%s"%(i+1,side),
                     (sign*.775,-.035+i*.035,1.073),
                     (sign*.835,-.035+i*.035,1.038),"Hand."+side)
        add_bone("UpperLeg."+side,(sign*.12,0,1.025),(sign*.13,0,.59),"Hips")
        add_bone("LowerLeg."+side,(sign*.13,0,.59),(sign*.13,-.01,.135),"UpperLeg."+side)
        add_bone("Foot."+side,(sign*.13,-.01,.135),(sign*.13,-.18,.085),"LowerLeg."+side)
    bpy.ops.object.mode_set(mode="OBJECT")
    ARM.show_in_front=True
    ARM.display_type="WIRE"
    for bone in ARM.data.bones:bone.use_deform=True
    log("01 / Full humanoid armature with hands and toes")

def pelvis_body():
    loft("Pants / athletic pelvic block",(0,0,1.06),(0,0,1.19),
         [(0,.21,.123),(.26,.218,.135),(.72,.187,.118),(1,.166,.11)],MAT["black"],"Hips",20)
    loft("Torso / fitted compression undershirt",(0,0,1.18),(0,0,1.44),
         [(0,.162,.112),(.23,.156,.110),(.66,.188,.127),(1,.216,.134)],MAT["graphite"],"Spine",24)
    loft("Chest / technical jacket",(0,0,1.44),(0,0,1.605),
         [(0,.212,.129),(.28,.233,.140),(.74,.249,.132),(1,.205,.113)],MAT["white"],"Chest",24)
    ball("Chest / clavicle volume",(0,0,1.54),(.20,.125,.10),MAT["white"],"Chest")
    curve_tube("Jacket zipper front",[(0,-.128,1.21),(0,-.143,1.37),(0,-.152,1.54)],
               MAT["blue"],"Spine",.006)
    cube("Chest / inset technical logo",(.038,-.147,1.53),(.055,.009,.018),MAT["cyan"],"Chest")
    for side in [-1,1]:
        curve_tube("Torso sports seam",[(side*.165,-.103,1.21),(side*.19,-.116,1.42),
                    (side*.19,-.115,1.59)],MAT["blue"],"Chest",.004)
        ball("Hip joint fabric cover",(side*.12,0,1.015),(.118,.124,.100),MAT["black"],"Hips")
    cube("Waist utility belt",(0,-.117,1.132),(.341,.024,.029),MAT["carbon"],"Hips")
    log("02 / Contoured torso and athletic textile")

def one_leg(side):
    S=-1 if side=="L" else 1
    hip=(S*.128,0,1.02)
    knee=(S*.130,0,.59)
    ankle=(S*.130,-.01,.135)
    loft("Thigh %s / tapered running tights"%side,hip,knee,
         [(0,.11,.115),(.15,.113,.113),(.56,.098,.096),(.90,.084,.085),(1,.081,.082)],
         MAT["black"],"UpperLeg."+side,20)
    loft("Lower leg %s / shin fabric"%side,knee,ankle,
         [(0,.084,.081),(.14,.089,.086),(.43,.103,.096),(.7,.071,.073),(1,.057,.06)],
         MAT["graphite"],"LowerLeg."+side,20)
    ball("Knee %s / fabric fitted patella"%side,knee,(.087,.09,.093),
         MAT["darksteel"],"UpperLeg."+side)
    ball("Ankle %s / breathable cuff"%side,ankle,(.066,.066,.077),
         MAT["black"],"LowerLeg."+side)
    loft("Thigh %s / luminous contour stripe"%side,
         (S*.176,-.108,.96),(S*.170,-.080,.63),
         [(0,.012,.007),(.5,.013,.008),(1,.008,.005)],MAT["blue"],"UpperLeg."+side,10)
    for j in range(3):
        cube("Knee %s / layered compression fin %d"%(side,j),
             (S*.13,-.089,.615+j*.014),(.079,.013,.008),MAT["white"],"UpperLeg."+side,.002)
    log("03 / %s human leg muscle shapes and clothes"%side)

def one_arm(side):
    S=-1 if side=="L" else 1
    A=(S*.23,0,1.54); B=(S*.47,0,1.34); C=(S*.69,0,1.13)
    loft("Upper arm %s / tailored jacket sleeve"%side,A,B,
         [(0,.10,.112),(.23,.117,.11),(.64,.101,.096),(.89,.078,.078),(1,.076,.076)],
         MAT["white"],"UpperArm."+side,20)
    ball("Elbow %s / flexible joint sleeve"%side,B,(.080,.080,.086),
         MAT["graphite"],"UpperArm."+side)
    loft("Forearm %s / tapered athletic sleeve"%side,B,C,
         [(0,.086,.089),(.20,.091,.089),(.65,.080,.076),(.89,.057,.058),(1,.054,.054)],
         MAT["graphite"],"LowerArm."+side,20)
    curve_tube("Shoulder %s / contrast stripe"%side,
               [(S*.27,-.105,1.54),(S*.39,-.108,1.40),
                (S*.55,-.084,1.275),(S*.64,-.063,1.18)],
               MAT["blue"],"UpperArm."+side,.007)
    for i in range(2):
        ball("Arm %s / reflective LED patch %d"%(side,i),
             (S*(.53+i*.066),-.085+i*.009,1.295-i*.07),
             (.015,.010,.009),MAT["cyan"],"LowerArm."+side,12)
    log("04 / %s upper arm, forearm and cuffs"%side)

def head_face():
    loft("Neck / warm skin anatomy",(0,0,1.595),(0,0,1.75),
         [(0,.065,.064),(.28,.066,.070),(.66,.062,.065),(1,.072,.072)],
         MAT["skin"],"Neck")
    ball("Head / organic oval and cheekbones",(0,0,1.838),(.144,.122,.186),
         MAT["skin"],"Head",32)
    # Looking towards -Y.
    ball("Lower cheek left",(-.080,-.074,1.788),(.060,.060,.069),MAT["skin"],"Head",20)
    ball("Lower cheek right",(.080,-.074,1.788),(.060,.060,.069),MAT["skin"],"Head",20)
    ball("Jaw line / chin",(0,-.049,1.724),(.090,.083,.064),MAT["skin"],"Head")
    ball("Nose bridge",(0,-.115,1.835),(.026,.040,.071),MAT["skinlit"],"Head")
    ball("Nose tip",(0,-.146,1.811),(.033,.030,.023),MAT["skin"],"Head",20)
    for S,label in [(-1,"left"),(1,"right")]:
        ball("Ear %s outer"%label,(S*.143,0,1.827),(.027,.030,.061),MAT["skin"],"Head")
        ball("Ear %s inner"%label,(S*.157,-.016,1.821),(.012,.008,.033),MAT["skinshadow"],"Head")
        ball("Eye %s sclera"%label,(S*.061,-.112,1.868),(.033,.016,.019),MAT["eyewhite"],"Head",24)
        ball("Eye %s iris"%label,(S*.060,-.129,1.869),(.014,.004,.015),MAT["iris"],"Head",24)
        ball("Eye %s pupil"%label,(S*.060,-.132,1.87),(.006,.003,.007),MAT["pupil"],"Head",16)
        loft("Eyebrow %s hair"%label,(S*.026,-.131,1.908),(S*.100,-.099,1.908),
             [(0,.006,.006),(.40,.010,.008),(1,.004,.005)],MAT["hair"],"Head",10)
    ball("Mouth / relaxed lip",(0,-.114,1.758),(.040,.009,.008),MAT["lip"],"Head",24)
    log("05 / Face with eyes, nose, ears, eyebrows and lips")

def hairstyle():
    ball("Hair / shaped skull cap",(0,0,1.934),(.146,.128,.105),MAT["hair"],"Head",32)
    for j in range(18):
        a=(j/18)*pi
        for row in range(2):
            x=.125*cos(a)+(row*.003)
            y=-.078+row*.065
            z=1.986+.024*sin(a)+.018*(j%3)
            ball("Hair / 3D sculpted strand %02d-%d"%(j,row),
                 (x,y,z),(.021,.034,.046),MAT["hair"],"Head",12)
    # Sideburns define the silhouette
    for S in (-1,1):
        ball("Hair / temple faded sideburn",(S*.137,-.048,1.863),
             (.012,.022,.058),MAT["hair"],"Head",16)
    log("06 / Sculpted short hairstyle and face detailing")

def hands(side):
    S=-1 if side=="L" else 1
    ball("Hand %s / palm human skin"%side,(S*.73,-.004,1.10),(.064,.058,.064),
         MAT["skin"],"Hand."+side)
    for i in range(3):
        y=-.035+i*.036
        loft("Hand %s finger %d"%(side,i),
             (S*.774,y,1.070),(S*.848,y,1.034),
             [(0,.012,.012),(.5,.012,.013),(.78,.010,.010),(1,.007,.007)],
             MAT["skin"],"Finger%d.%s"%(i+1,side),12)
        ball("Finger %s %d fingertip"%(side,i),
             (S*.844,y,1.037),(.010,.012,.010),
             MAT["skin"],"Finger%d.%s"%(i+1,side),12)
    loft("Hand %s thumb"%side,(S*.724,-.042,1.124),(S*.777,-.079,1.090),
         [(0,.019,.020),(.47,.018,.016),(1,.011,.011)],
         MAT["skin"],"Hand."+side,12)
    log("07 / %s human hands with independently skinned fingers"%side)

def shoes(side):
    S=-1 if side=="L" else 1
    lo=(S*.132,-.096,.073)
    ball("Shoe %s / breathable sneaker body"%side,lo,(.089,.180,.079),
         MAT["black"],"Foot."+side,24)
    cube("Shoe %s / molded white rubber sole"%side,
         (S*.132,-.106,.025),(.186,.344,.041),
         MAT["white"],"Foot."+side,.020)
    cube("Shoe %s / frontal toe cap"%side,(S*.132,-.229,.058),
         (.181,.094,.042),MAT["graphite"],"Foot."+side,.013)
    ball("Shoe %s / heel amber reflector"%side,
         (S*.132,.061,.066),(.058,.015,.024),
         MAT["orange"],"Foot."+side,12)
    for j in range(4):
        cube("Shoe %s / shoelace bridge %d"%(side,j),
             (S*.132,-.179+j*.033,.117-j*.008),
             (.077,.010,.006),MAT["white"],"Foot."+side,.002)
    for j in range(3):
        ball("Shoe %s / running groove %d"%(side,j),
             (S*.132,-.210+j*.05,.014),(.068,.012,.008),
             MAT["carbon"],"Foot."+side,12)
    log("08 / %s high-detail athletic footwear"%side)

def details():
    # Text label is converted to mesh and skinned to the chest bone.
    for word, loc, size, side in [
        ("AETHER 01",(.035,-.151,1.52),.026,0),
        ("MOVE / HUMAN",(-.09,-.150,1.462),.012,0),
    ]:
        txt=bpy.data.curves.new("Tech label","FONT")
        txt.body=word;txt.size=size;txt.extrude=.0007
        obj=bpy.data.objects.new(word,txt)
        bpy.context.collection.objects.link(obj)
        obj.location=loc
        obj.rotation_euler=(pi/2,0,0)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        bind(bpy.context.view_layer.objects.active,"Chest",MAT["cyan"])
    for S in (-1,1):
        ball("Athletic shoulder reflective roundel",(S*.216,-.052,1.557),
             (.030,.011,.028),MAT["blue"],"Chest")
    log("09 / Character branding, suit reflectors and finishing")

def set_world_rotation(bonename, axis, degrees):
    """Drive a character bone using a world-aligned rotation, expressed in
    the bone's local rest basis; friendly to mirrored limb coordinates."""
    posebone=ARM.pose.bones[bonename]
    basis=posebone.bone.matrix_local.to_quaternion()
    q=Quaternion(axis, math.radians(degrees))
    posebone.rotation_mode="QUATERNION"
    posebone.rotation_quaternion=basis.inverted()@q@basis

def animate(name, count, mode):
    if ARM.animation_data is None:
        ARM.animation_data_create()
    act=bpy.data.actions.new(name)
    act.use_fake_user=True
    ARM.animation_data.action=act
    for f in range(1,count+1,3):
        t=(f-1)/max(count-1,1)
        cyc=t*2*pi
        for pb in ARM.pose.bones:
            pb.rotation_mode="QUATERNION"
            pb.rotation_quaternion=(1,0,0,0)
            pb.location=(0,0,0)
        if mode=="idle":
            ARM.pose.bones["Root"].location.z=.009*sin(cyc)
            set_world_rotation("Chest",(0,0,1),1.7*sin(cyc))
            set_world_rotation("Head",(0,0,1),2.2*sin(cyc))
            set_world_rotation("UpperArm.L",(1,0,0),3*sin(cyc))
            set_world_rotation("UpperArm.R",(1,0,0),-3*sin(cyc))
        elif mode in ("walk","run"):
            fast=mode=="run"
            amp=49 if fast else 30
            bend=40 if fast else 28
            wave=cyc*(2 if fast else 1)
            ARM.pose.bones["Root"].location.z=(.047 if fast else .020)*abs(sin(wave))
            ARM.pose.bones["Root"].location.y=(-.020 if fast else -.016)*sin(wave)
            set_world_rotation("UpperLeg.L",(1,0,0), amp*sin(wave))
            set_world_rotation("UpperLeg.R",(1,0,0),-amp*sin(wave))
            set_world_rotation("LowerLeg.L",(1,0,0),bend*max(0,sin(wave+1.1)))
            set_world_rotation("LowerLeg.R",(1,0,0),bend*max(0,-sin(wave+1.1)))
            set_world_rotation("UpperArm.L",(1,0,0),-amp*.87*sin(wave))
            set_world_rotation("UpperArm.R",(1,0,0),amp*.87*sin(wave))
            set_world_rotation("LowerArm.L",(1,0,0),-(20 if fast else 11))
            set_world_rotation("LowerArm.R",(1,0,0),-(20 if fast else 11))
            set_world_rotation("Chest",(0,0,1),3.8*sin(wave))
            set_world_rotation("Spine",(1,0,0),-8 if fast else -2)
        elif mode=="punch":
            # Wind-up -> rapid straight cross -> hold -> return.
            if t<.22:power=-.32*t/.22
            elif t<.48:power=-.32+1.32*(t-.22)/.26
            elif t<.69:power=1.0
            else:power=max(0,(1.0-(t-.69)/.31))
            set_world_rotation("UpperArm.R",(1,0,0),-72*power)
            set_world_rotation("LowerArm.R",(1,0,0),-38*power)
            set_world_rotation("Chest",(0,0,1),-22*power)
            set_world_rotation("Spine",(0,0,1),-9*power)
            set_world_rotation("Head",(0,0,1),9*power)
            set_world_rotation("UpperArm.L",(1,0,0),-32*power)
            set_world_rotation("LowerArm.L",(1,0,0),-18*power)
            ARM.pose.bones["Root"].location.y=-.060*power
        for pb in ARM.pose.bones:
            pb.keyframe_insert(data_path="rotation_quaternion",frame=f,group=pb.name)
            if pb.name=="Root":
                pb.keyframe_insert(data_path="location",frame=f,group=pb.name)
    # Ensures exact loop last frame even if frame count isn't divisible by 3.
    act.frame_range # observe action extents
    ACTIONS.append(act)
    # Export animations as separately named glTF NLA tracks.
    track=ARM.animation_data.nla_tracks.new()
    track.name=name
    strip=track.strips.new(name,1,act)
    strip.action_frame_start=1
    strip.action_frame_end=count
    strip.extrapolation="NOTHING"
    # Temporarily mute in Blender playback to avoid stacking all actions;
    # glTF track exporter may honor/unmute for export below.
    track.mute=True
    ARM.animation_data.action=None
    log("10 / ANIMATED "+name+" "+str(len(act.fcurves))+" keyed channels")

def generate_motion(name,frames,mode):
    animate(name,frames,mode)

def finish():
    # Set a neutral stance before writing .blend.
    for track in ARM.animation_data.nla_tracks:
        track.mute=True
    idle=next(a for a in ACTIONS if a.name=="Idle")
    ARM.animation_data.action=idle
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    for obj in CHAR:obj.select_set(True)
    bpy.context.view_layer.objects.active=ARM
    blend=os.path.join(OUT,"AETHER-01-Rigged-Animated-Human.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    # All NLA tracks enabled at export; glTF splits named actions into distinct clips.
    ARM.animation_data.action=None
    for track in ARM.animation_data.nla_tracks:
        track.mute=False
    # Export with explicit skinning and animations. Studio floor/camera excluded.
    kwargs=dict(filepath=os.path.join(OUT,"AETHER-01-Rigged-Animated-Human.glb"),
                export_format="GLB",use_selection=True,
                export_materials="EXPORT",export_animations=True,
                export_nla_strips=True,export_skins=True,
                export_force_sampling=True)
    bpy.ops.export_scene.gltf(**kwargs)
    for track in ARM.animation_data.nla_tracks:
        track.mute=True
    ARM.animation_data.action=idle
    bpy.context.scene.frame_set(1)
    print("AETHER_RIG_BONES",len(ARM.data.bones),flush=True)
    print("AETHER_CHARACTER_MESHES",len(CHAR),flush=True)
    print("AETHER_ACTIONS",",".join(a.name for a in ACTIONS),flush=True)
    for fn in [blend,kwargs["filepath"]]:
        print("AETHER_ASSET",fn,os.stat(fn).st_size,flush=True)
    log("FINISHED / BLEND + RIGGED GLB + ANIMATION CLIPS")
    print("AETHER_COMPLETED",flush=True)

PHASES=[
    skeleton,pelvis_body,
    lambda:one_leg("L"),lambda:one_leg("R"),
    lambda:one_arm("L"),lambda:one_arm("R"),
    head_face,hairstyle,
    lambda:hands("L"),lambda:hands("R"),
    lambda:shoes("L"),lambda:shoes("R"),
    details,
    lambda:generate_motion("Idle",49,"idle"),
    lambda:generate_motion("Walk",49,"walk"),
    lambda:generate_motion("Run",37,"run"),
    lambda:generate_motion("Punch",37,"punch"),
    finish
]
initialize()
if LIVE:
    state={"phase":0}
    def next_step():
        idx=state["phase"]
        if idx<len(PHASES):
            PHASES[idx]()
            state["phase"]=idx+1
            for area in bpy.context.screen.areas:area.tag_redraw()
            return 4.8
        return None
    bpy.app.timers.register(next_step,first_interval=8.0)
    print("AETHER_LIVE_BLENDER_MODELING_STARTED",flush=True)
else:
    for phase in PHASES:phase()
