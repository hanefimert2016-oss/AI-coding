#!/usr/bin/env python3
"""KINETIC HUMAN v1: procedural organic human, skinned skeleton, and four
authored actions. Run inside Blender 4.0 via its REAL graphical session.
Output: blend, animated glb, live recorded modeling/animation phases.
"""
import bpy, math, os, sys, json, struct
from mathutils import Vector
from math import pi, sin, cos

args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT=os.path.abspath(args[0] if args else "/tmp/kinetic-human")
LIVE="--live" in args
os.makedirs(OUT,exist_ok=True)
BODY=[]
PROPS=[]
M={}
RIG=None
ACTIONS={}
PREVIEW=None
PREVIEW_FRAME=1
STEPS=0

def mat(name,rgb,metal=0.0,rough=.55,emission=0.0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*rgb,1.0)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    if emission:
        p.inputs["Emission Color"].default_value=(*rgb,1)
        p.inputs["Emission Strength"].default_value=emission
    return m

def all_mats():
    palette={
        "skin":("Skin | warm natural complexion",(.62,.382,.265),0.0,.54),
        "skinlight":("Skin | nose ear and fingertip",(.73,.475,.343),0.0,.56),
        "hair":("Hair | deep chestnut",(.077,.045,.034),0.05,.57),
        "hairshine":("Hair | warm highlights",(.18,.096,.054),0.03,.5),
        "eyes":("Eyes | warm off-white",(.87,.82,.72),0.0,.29),
        "iris":("Eyes | amber brown",(.145,.071,.033),0.0,.23),
        "black":("Eyes | pupils",(.009,.009,.012),0.0,.16),
        "lips":("Natural lips",(.48,.245,.228),0,.59),
        "brow":("Dark eyebrows",(.12,.063,.042),0,.7),
        "jacket":("Training jacket | deep navy",(.044,.091,.151),.05,.56),
        "jacket_shadow":("Soft stretch textile | charcoal",(.037,.052,.070),.01,.73),
        "jacket_light":("Sportswear shoulder contrast",(.10,.19,.27),.03,.58),
        "pants":("Training trousers | graphite",(.072,.095,.12),0,.69),
        "trim":("Sportswear teal seam",(.024,.72,.66),.05,.36),
        "zipper":("Zipper | anodized alloy",(.65,.75,.78),.75,.25),
        "sole":("Sneaker sole | cloud white",(.78,.80,.78),0,.72),
        "shoe":("Sneaker fabric | graphite",(.09,.13,.15),0,.63),
        "shoeaccent":("Sneaker accented tongue",(.92,.42,.22),0,.46),
        "ground":("Matte studio floor",(.047,.063,.081),0,.84)
    }
    for key,(name,rgb,metal,rough) in palette.items():
        M[key]=mat(name,rgb,metal,rough)

def mesh_obj(name,verts,faces,material,bone,weights=None):
    mesh=bpy.data.meshes.new(name+" topology")
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(M[material])
    for poly in mesh.polygons:poly.use_smooth=True
    if weights:
        for group_name,weight_list in weights.items():
            vg=obj.vertex_groups.new(name=group_name)
            for i,w in enumerate(weight_list):
                if w>0:vg.add([i],float(min(1.0,w)),"REPLACE")
    else:
        vg=obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(verts))),1.0,"REPLACE")
    mod=obj.modifiers.new("KINETIC deform | armature skeleton","ARMATURE")
    mod.object=RIG
    obj.parent=RIG
    BODY.append(obj)
    return obj

def sphere(name,pt,scales,material,bone,seg=24,rings=16):
    x,y,z=pt
    verts=[]
    faces=[]
    for v in range(rings+1):
        phi=pi*v/rings
        for s in range(seg):
            t=2*pi*s/seg
            verts.append((x+scales[0]*sin(phi)*cos(t),
                          y+scales[1]*sin(phi)*sin(t),
                          z+scales[2]*cos(phi)))
    for v in range(rings):
        for s in range(seg):
            a=v*seg+s
            b=v*seg+(s+1)%seg
            faces.append((a,b,b+seg,a+seg))
    return mesh_obj(name,verts,faces,material,bone)

def tube(name,a,b,radii,material,bone,sides=24,rings=9,bulge=0):
    """Shaped elliptical limb running between specified anatomical landmarks."""
    a=Vector(a);b=Vector(b);vec=(b-a)
    tangent=vec.normalized()
    horizontal=Vector((0,1,0))
    if abs(tangent.dot(horizontal))>.92:horizontal=Vector((1,0,0))
    xaxis=tangent.cross(horizontal).normalized()
    yaxis=tangent.cross(xaxis).normalized()
    verts=[];faces=[]
    for i in range(rings+1):
        t=i/rings
        mid=a.lerp(b,t)
        # Taper is natural: wide near anatomical muscle, compact at joints.
        radius_factor=.83+.17*sin(pi*t)
        if bulge:radius_factor+=bulge*sin(pi*t)
        for j in range(sides):
            angle=2*pi*j/sides
            p=mid+xaxis*cos(angle)*radii[0]*radius_factor+yaxis*sin(angle)*radii[1]*radius_factor
            verts.append(tuple(p))
    for i in range(rings):
        for j in range(sides):
            l=i*sides+j
            k=i*sides+(j+1)%sides
            faces.append((l,k,k+sides,l+sides))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(rings*sides+j for j in range(sides)))
    return mesh_obj(name,verts,faces,material,bone)

def torso(name,ring_specs,material,bones=("Pelvis","Spine","Chest"),sides=48):
    """Organic elliptical torso with softly transitioning bone weights."""
    verts=[];faces=[]
    weights={b:[] for b in bones}
    for z,cx,cy,rx,ry in ring_specs:
        for j in range(sides):
            angle=2*pi*j/sides
            # Mild asymmetric pec / ribcage anatomical definition.
            x=cx+rx*cos(angle)
            y=cy+ry*sin(angle)
            if z>1.40 and sin(angle)<-.1:
                y-=.006*(1-abs(cos(angle)))
            verts.append((x,y,z))
            if z<=1.24:
                w=(1.0,0,0)
            elif z<1.44:
                t=(z-1.24)/.20
                w=(0,max(0,1.0-t),max(0,t)) if z>1.31 else (max(0,(1.32-z)/.08),min(1,(z-1.24)/.08),0)
            else:
                w=(0,0,1.0)
            if z>=1.31 and z<1.44:w=(0,1.0-(z-1.31)/.13,(z-1.31)/.13)
            total=sum(w)
            for bone,weight in zip(bones,w):
                weights[bone].append(weight/total if total else 0)
    for i in range(len(ring_specs)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),
                  tuple((len(ring_specs)-1)*sides+j for j in range(sides))])
    return mesh_obj(name,verts,faces,material,"Spine",weights)

def line(name,points,radius,material,bone):
    for i in range(len(points)-1):
        tube(name+" segment %d"%i,points[i],points[i+1],(radius,radius),material,bone,sides=10,rings=2)

def setup():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    all_mats()
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1400
    scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    scene.frame_start=1
    scene.frame_end=96
    world=bpy.data.worlds.new("Studio | low contrast") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world=world
    world.color=(.06,.07,.08)
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor=bpy.context.object
    floor.name="STUDIO / FLOOR"
    floor.location.z=-.024
    floor.data.materials.append(M["ground"])
    PROPS.append(floor)
    for name,pt,energy,color,size in [
        ("Softbox | key",(-3.0,-4.5,5.5),2200,(1,.87,.78),4.5),
        ("Softbox | rim",(2.6,3.5,4.8),2300,(.37,.70,1.0),4.0),
        ("Softbox | front",(2.7,-2,4),1600,(1,1,1),4.0)]:
        d=bpy.data.lights.new(name,"AREA")
        d.energy=energy;d.color=color;d.size=size
        ob=bpy.data.objects.new(name,d)
        bpy.context.collection.objects.link(ob)
        ob.location=pt;PROPS.append(ob)
    d=bpy.data.cameras.new("Studio portrait | 70mm")
    c=bpy.data.objects.new("CAMERA | Human full body",d)
    bpy.context.collection.objects.link(c)
    c.location=(3.1,-5.3,2.65)
    c.rotation_euler=(Vector((0,0,1.02))-c.location).to_track_quat("-Z","Y").to_euler()
    d.type="ORTHO";d.ortho_scale=2.72
    scene.camera=c
    PROPS.append(c)
    if LIVE:
        try: bpy.context.preferences.view.show_splash=False
        except:pass
        for area in bpy.context.screen.areas:
            if area.type=="VIEW_3D":
                space=area.spaces.active
                space.region_3d.view_perspective='CAMERA'
                space.region_3d.view_camera_zoom=4
                space.shading.type='SOLID'
                space.shading.color_type='MATERIAL'
                space.shading.show_cavity=True
                space.shading.cavity_type='BOTH'
                space.overlay.show_floor=False
                space.overlay.show_axis_x=False
                space.overlay.show_axis_y=False
                space.overlay.show_cursor=False
                space.overlay.show_extras=False
                area.tag_redraw()
    print("HUMAN_PHASE 00 / scene and visual presentation",flush=True)

def skeleton():
    global RIG
    arm=bpy.data.armatures.new("Human skeleton | 19 deform bones")
    RIG=bpy.data.objects.new("KINETIC_HUMAN_RIG",arm)
    bpy.context.collection.objects.link(RIG)
    bpy.context.view_layer.objects.active=RIG
    RIG.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    data=[
        ("Root",(0,0,.99),(0,0,1.10),None),
        ("Pelvis",(0,0,1.05),(0,0,1.18),"Root"),
        ("Spine",(0,0,1.18),(0,0,1.42),"Pelvis"),
        ("Chest",(0,0,1.42),(0,0,1.60),"Spine"),
        ("Neck",(0,0,1.60),(0,0,1.74),"Chest"),
        ("Head",(0,0,1.74),(0,0,1.95),"Neck"),
    ]
    for sign,side in [(-1,"R"),(1,"L")]:
        data.extend([
            ("Thigh."+side,(sign*.135,0,1.055),(sign*.142,0,.615),"Pelvis"),
            ("Shin."+side,(sign*.142,0,.615),(sign*.15,0,.135),"Thigh."+side),
            ("Foot."+side,(sign*.15,0,.135),(sign*.15,-.24,.10),"Shin."+side),
            ("UpperArm."+side,(sign*.243,0,1.558),(sign*.495,0,1.337),"Chest"),
            ("Forearm."+side,(sign*.495,0,1.337),(sign*.710,0,1.138),"UpperArm."+side),
            ("Hand."+side,(sign*.710,0,1.138),(sign*.798,-.035,1.098),"Forearm."+side),
        ])
    bones={}
    for name,head,tail,parent in data:
        bone=arm.edit_bones.new(name);bone.head=head;bone.tail=tail
        if parent:bone.parent=bones[parent]
        bones[name]=bone
    bpy.ops.object.mode_set(mode="OBJECT")
    RIG.show_in_front=True
    for pb in RIG.pose.bones:pb.rotation_mode='XYZ'
    print("HUMAN_PHASE 01 / armature bones",len(RIG.data.bones),flush=True)

def body():
    specs=[
        (1.07,0,0,.180,.118),
        (1.14,0,0,.196,.120),
        (1.22,0,0,.174,.108),
        (1.32,0,0,.161,.108),
        (1.41,0,0,.185,.118),
        (1.48,0,0,.238,.133),
        (1.54,0,0,.243,.129),
        (1.59,0,0,.197,.104),
    ]
    torso("Sculpted upper body | textile training jacket",specs,"jacket",sides=56)
    torso("Elastic waist band | charcoal panel",
          [(1.12,0,0,.189,.128),(1.17,0,0,.188,.126),
           (1.20,0,0,.172,.113)],"jacket_shadow",sides=48)
    tube("Neck | anatomical neck",(0,0,1.59),(0,0,1.738),(.066,.061),"skin","Neck",sides=32)
    sphere("Neck collar undercut",(0,0,1.62),(.099,.076,.043),"jacket_shadow","Chest")
    # Two-color shoulder/collar detailing, flat fabrics laid over underlying body.
    for s,side in [(-1,"right"),(1,"left")]:
        sphere("Shoulder muscle | "+side,(s*.204,0,1.540),(.088,.108,.091),"jacket_light","Chest")
        line("Jacket shoulder piping "+side,[
            (s*.079,-.115,1.558),(s*.183,-.127,1.562),(s*.250,-.084,1.535)],
            .008,"trim","Chest")
    tube("Jacket front seam zip",(0,-.131,1.542),(0,-.122,1.19),(.008,.008),"zipper","Chest",sides=12)
    sphere("Zip fastening head",(0,-.143,1.495),(.014,.009,.019),"zipper","Chest")
    line("Torso side body panel left",[(.15,-.06,1.22),(.18,-.093,1.43)],.005,"trim","Spine")
    line("Torso side body panel right",[(-.15,-.06,1.22),(-.18,-.093,1.43)],.005,"trim","Spine")
    print("HUMAN_PHASE 02 / organic torso and athletic jacket",len(BODY),flush=True)

def legs():
    for s,side in [(-1,"R"),(1,"L")]:
        hip=(s*.137,0,1.05);knee=(s*.144,0,.612);ankle=(s*.15,0,.135)
        tube("Muscular thigh "+side,hip,knee,(.101,.108),
             "pants","Thigh."+side,sides=40,rings=14,bulge=.09)
        sphere("Knee cloth joint "+side,knee,(.085,.094,.081),"pants","Shin."+side,seg=32)
        tube("Tapered shin "+side,knee,ankle,(.079,.081),
             "pants","Shin."+side,sides=40,rings=14,bulge=.08)
        tube("Trouser cuff "+side,(s*.15,0,.191),(s*.15,0,.139),
             (.075,.079),"jacket_shadow","Shin."+side,sides=32,rings=3)
        # Human sneaker silhouette: ankles, upper and elongated toe.
        sphere("Anatomical sneaker heel "+side,(s*.15,-.036,.081),
               (.104,.145,.083),"shoe","Foot."+side)
        sphere("Foot toe upper "+side,(s*.15,-.181,.070),
               (.110,.132,.063),"shoe","Foot."+side)
        sphere("Sneaker outer sole "+side,(s*.15,-.132,.025),
               (.109,.201,.026),"sole","Foot."+side)
        sphere("Sneaker bright tongue "+side,(s*.15,-.093,.138),
               (.069,.081,.020),"shoeaccent","Foot."+side)
        for j in range(4):
            z=.123-.013*j
            line("Sneaker laces "+side+" "+str(j),
                 [(s*.15-.041,-.112-.026*j,z),
                  (s*.15+.041,-.112-.026*j,z)],
                 .0038,"sole","Foot."+side)
        for j in range(3):
            z=.40+j*.075
            line("Trouser seam "+side+" "+str(j),
                 [(s*.23,0,z),(s*.23,0,z+.052)],
                 .004,"jacket_light","Shin."+side)
    print("HUMAN_PHASE 03 / full legs, knees, ankles and running shoes",len(BODY),flush=True)

def arms():
    for s,side in [(-1,"R"),(1,"L")]:
        shoulder=(s*.245,0,1.56);elbow=(s*.498,0,1.34)
        wrist=(s*.715,0,1.142);knuckle=(s*.798,-.034,1.102)
        tube("Sculpted upper arm sleeve "+side,shoulder,elbow,
             (.092,.091),"jacket","UpperArm."+side,sides=36,rings=12,bulge=.12)
        sphere("Soft elbow panel "+side,elbow,
               (.074,.077,.073),"jacket_light","Forearm."+side)
        tube("Forearm anatomical sleeve "+side,elbow,wrist,
             (.078,.075),"jacket","Forearm."+side,sides=36,rings=12,bulge=.05)
        tube("Cuff sportswear "+side,
             tuple(Vector(wrist)-Vector((s*.035,0,-.035))),wrist,
             (.074,.067),"jacket_shadow","Forearm."+side,sides=24,rings=4)
        sphere("Hand palm "+side,
               tuple((Vector(wrist)+Vector(knuckle))*.5),
               (.074,.066,.064),"skin","Hand."+side,seg=32)
        # Individual hand shapes, no mitten-like wrist for rig preview.
        for j in range(4):
            spread=(j-1.5)*.027
            start=(s*(.790+spread*.1),-.024+spread,1.106)
            end=(s*(.853+(1.5-abs(j-1.5))*.010),-.065+spread,1.066)
            tube("Finger %s %d"%(side,j),start,end,(.013,.014),"skinlight",
                 "Hand."+side,sides=12,rings=4)
        tube("Thumb "+side,(s*.751,-.054,1.132),(s*.791,-.114,1.083),
             (.020,.018),"skin","Hand."+side,sides=16,rings=4)
        line("Sleeve fluorescent stripe "+side,[
            (s*.29,-.082,1.52),(s*.405,-.080,1.41),(s*.48,-.075,1.35)],
            .0065,"trim","UpperArm."+side)
        line("Lower sleeve seam "+side,[
            (s*.535,-.080,1.305),(s*.65,-.073,1.191)],
            .0055,"jacket_light","Forearm."+side)
    print("HUMAN_PHASE 04 / articulated arms and individual fingers",len(BODY),flush=True)

def face():
    # Skull/jaw anatomy + ear helix + eyebrows, nose, mouth, eyes.
    sphere("Organic face and cranium",(0,-.001,1.826),
           (.110,.102,.147),"skin","Head",seg=48,rings=32)
    sphere("Lower jaw and chin",(0,-.012,1.756),
           (.078,.083,.050),"skin","Head",seg=32)
    for s,side in [(-1,"R"),(1,"L")]:
        sphere("Real human ear "+side,(s*.107,-.002,1.814),
               (.030,.019,.049),"skinlight","Head",seg=24)
        sphere("Ear concha "+side,(s*.124,-.021,1.812),
               (.009,.010,.025),"skin","Head",seg=16)
        sphere("Eyeball "+side,(s*.042,-.090,1.842),
               (.027,.012,.016),"eyes","Head",seg=28)
        sphere("Iris "+side,(s*.042,-.102,1.843),
               (.014,.005,.013),"iris","Head",seg=24)
        sphere("Pupil "+side,(s*.042,-.108,1.843),
               (.007,.003,.008),"black","Head",seg=18)
        sphere("Eye glint "+side,(s*.039,-.112,1.847),
               (.0025,.0015,.0026),"eyes","Head",seg=12)
        tube("Subtle brow arch "+side,
             (s*.016,-.097,1.870),(s*.070,-.077,1.879),
             (.008,.007),"brow","Head",sides=12,rings=4)
        sphere("Cheek tissue "+side,(s*.060,-.070,1.794),
               (.040,.025,.029),"skin","Head",seg=24)
    sphere("Nose bridge",(0,-.094,1.819),
           (.024,.019,.039),"skinlight","Head")
    sphere("Nose tip",(0,-.119,1.793),
           (.024,.018,.015),"skinlight","Head")
    for s in (-1,1):
        sphere("Nostril alar "+str(s),(s*.015,-.116,1.784),
               (.012,.007,.010),"skin","Head")
    sphere("Natural mouth upper lip",(0,-.084,1.760),
           (.033,.011,.006),"lips","Head")
    sphere("Natural mouth lower lip",(0,-.085,1.751),
           (.028,.009,.005),"skinlight","Head")
    print("HUMAN_PHASE 05 / human facial anatomy and expression",len(BODY),flush=True)

def hair():
    sphere("Short dark swept hairstyle | scalp",
           (0,.009,1.947),(.112,.101,.060),"hair","Head",seg=36)
    # Strand tufts are asymmetrical and angular, preserving believable hairstyle
    # without a solid helmet effect.
    for j in range(11):
        x=-.086+j*.0175
        z=1.973 + .018*sin(j*.48)
        start=(x,-.084,z-.023)
        end=(x+.012,-.109,z+.011)
        tube("Forehead textured hair lock %02d"%j,start,end,
             (.017,.010),"hair" if j%3 else "hairshine","Head",sides=12,rings=4)
    for s,side in [(-1,"R"),(1,"L")]:
        for j in range(6):
            z=1.844+j*.023
            sphere("Side swept hair texture "+side+" "+str(j),
                   (s*.097,-.005,z),(.017,.041,.018),
                   "hair" if j%2 else "hairshine","Head",seg=16)
    print("HUMAN_PHASE 06 / natural short hair and sculpted texture",len(BODY),flush=True)

def details():
    # Jacket shoulders, reflective fabrics and functional running clothes.
    for s,side in [(-1,"R"),(1,"L")]:
        line("Chest reflective piping "+side,[
             (s*.035,-.134,1.519),(s*.112,-.142,1.467),
             (s*.165,-.111,1.386)],.006,"trim","Chest")
        sphere("Jacket chest badge "+side,(s*.170,-.128,1.492),
               (.022,.008,.018),"shoeaccent","Chest",seg=18)
        line("Pants side outseam "+side,[
             (s*.216,-.002,.995),(s*.225,-.018,.76),
             (s*.215,-.024,.51),(s*.219,-.032,.25)],
             .005,"jacket_light","Thigh."+side)
        sphere("Shoe reflective heel disk "+side,
               (s*.15,.067,.084),(.044,.009,.019),
               "trim","Foot."+side)
    sphere("Logo chest center",(0,-.138,1.480),
           (.020,.007,.023),"zipper","Chest")
    print("HUMAN_PHASE 07 / sewing details, fabric seams, badges",len(BODY),flush=True)

def key_all(frame,rotations=None,root_raise=0,hip_tilt=0):
    rotations=rotations or {}
    for p in RIG.pose.bones:
        rot=rotations.get(p.name,(0,0,0))
        p.rotation_euler=rot
        p.keyframe_insert(data_path="rotation_euler",frame=frame,group=p.name)
    root=RIG.pose.bones["Root"]
    root.location=(0,0,root_raise)
    root.keyframe_insert(data_path="location",frame=frame,group="Root")

def create_action(name,frames,func,loop=False):
    act=bpy.data.actions.new(name=name)
    act.use_fake_user=True
    RIG.animation_data.action=act
    for frame in frames:
        rotations,bob=func(frame)
        key_all(frame,rotations,root_raise=bob)
    if loop:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:kp.interpolation="LINEAR"
    else:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:kp.interpolation="BEZIER"
    ACTIONS[name]=act
    return act

def build_actions():
    RIG.animation_data_create()
    def idle(f):
        t=2*pi*(f-1)/96
        return ({"Chest":(.014*sin(t),0,.015*sin(t*.5)),
                 "Head":(.012*cos(t),.010*sin(t),0),
                 "UpperArm.L":(.020*sin(t),0,0),
                 "UpperArm.R":(-.020*sin(t),0,0)},.008*sin(t))
    def walk(f):
        t=2*pi*(f-1)/48
        s=sin(t)
        return ({
            "Thigh.L":(.53*s,0,.03),
            "Shin.L":(.54*max(0,-s),0,0),
            "Foot.L":(-.14*s,0,0),
            "Thigh.R":(-.53*s,0,-.03),
            "Shin.R":(.54*max(0,s),0,0),
            "Foot.R":(.14*s,0,0),
            "UpperArm.L":(-.34*s,0,0),
            "Forearm.L":(-.17,0,0),
            "UpperArm.R":(.34*s,0,0),
            "Forearm.R":(.17,0,0),
            "Chest":(.025*sin(2*t),.015*sin(t),.029*sin(t)),
            "Head":(-.025*sin(t),0,-.012*sin(t))},
            .027*abs(sin(t)))
    def run(f):
        t=2*pi*(f-1)/32
        s=sin(t)
        return ({
            "Thigh.L":(.83*s,0,.06),
            "Shin.L":(.93*max(0,-s),0,0),
            "Thigh.R":(-.83*s,0,-.06),
            "Shin.R":(.93*max(0,s),0,0),
            "Foot.L":(-.18*s,0,0),
            "Foot.R":(.18*s,0,0),
            "UpperArm.L":(-.65*s,0,-.12),
            "Forearm.L":(-.62,0,0),
            "UpperArm.R":(.65*s,0,.12),
            "Forearm.R":(.62,0,0),
            "Chest":(.16,0,.04*sin(t)),
            "Head":(-.09,0,-.015*sin(t))},
            .075*abs(sin(t)))
    def punch(f):
        # Right-hand straight punch. Front is negative Y.
        progress=(f-1)/48
        attack=max(0,min(1,(progress-.15)/.23))
        recoil=max(0,min(1,(progress-.59)/.18))
        hit=attack*(1-recoil)
        guard=min(1,progress*6)
        return ({
            "Chest":(.05*hit,0,-.21*hit),
            "Spine":(.025*hit,0,-.08*hit),
            "UpperArm.R":(-.37*guard-.30*hit,.12*hit,-1.18*hit),
            "Forearm.R":(-.48*guard+.61*hit,0,.26*hit),
            "Hand.R":(.07*hit,0,0),
            "UpperArm.L":(-.39*guard,0,.12*guard),
            "Forearm.L":(-.52*guard,0,.04),
            "Head":(-.055*hit,0,.13*hit),
            "Thigh.R":(.10*hit,0,0),
            "Thigh.L":(-.055*hit,0,0)},
            -.024*hit)
    create_action("Idle_Breathing",list(range(1,97,8))+[97],idle,True)
    create_action("Walk_Loop",list(range(1,49,3))+[49],walk,True)
    create_action("Run_Loop",list(range(1,33,2))+[33],run,True)
    create_action("Punch_Right_Jab",list(range(1,49,3))+[49],punch,False)
    # one NLA track per action is a standard glTF-readable clip.
    for name,act in ACTIONS.items():
        track=RIG.animation_data.nla_tracks.new()
        track.name=name
        strip=track.strips.new(name,1,act)
        track.mute=True
    RIG.animation_data.action=None
    print("HUMAN_PHASE 08 / authored four skeletal animation tracks",
          [(n,len(a.fcurves)) for n,a in ACTIONS.items()],flush=True)

def pose(name,frame):
    global PREVIEW,PREVIEW_FRAME
    PREVIEW=name
    PREVIEW_FRAME=frame
    for track in RIG.animation_data.nla_tracks:
        track.mute=True
    RIG.animation_data.action=ACTIONS[name]
    bpy.context.scene.frame_set(frame)
    print("ANIMATION_PREVIEW",name,frame,flush=True)

def phase_idle():
    pose("Idle_Breathing",16)
    print("HUMAN_PHASE 09 / breathing animation preview",flush=True)

def phase_walk():
    pose("Walk_Loop",9)
    print("HUMAN_PHASE 10 / walking animation preview",flush=True)

def phase_run():
    pose("Run_Loop",8)
    print("HUMAN_PHASE 11 / running animation preview",flush=True)

def phase_punch():
    pose("Punch_Right_Jab",21)
    print("HUMAN_PHASE 12 / right-hand boxing jab preview",flush=True)

def verify_glb(path):
    data=open(path,"rb").read()
    assert data[:4]==b'glTF' and struct.unpack_from("<I",data,4)[0]==2
    n=struct.unpack_from("<I",data,12)[0]
    return json.loads(data[20:20+n])

def save():
    for track in RIG.animation_data.nla_tracks:track.mute=True
    pose("Idle_Breathing",1)
    path=os.path.join(OUT,"KINETIC-HUMAN-Rigged-Animated.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.object.select_all(action="DESELECT")
    RIG.select_set(True)
    for o in BODY:o.select_set(True)
    bpy.context.view_layer.objects.active=RIG
    glb=os.path.join(OUT,"KINETIC-HUMAN-Rigged-Animated.glb")
    options={
        "filepath":glb,
        "export_format":"GLB",
        "use_selection":True,
        "export_materials":"EXPORT",
        "export_animations":True,
        "export_nla_strips":False,
    }
    bpy.ops.export_scene.gltf(**options)
    meta=verify_glb(glb)
    if len(meta.get("animations",[]))<4:
        print("ACTION_EXPORT_FALLBACK_NLA_TRACKS",len(meta.get("animations",[])),flush=True)
        for track in RIG.animation_data.nla_tracks:track.mute=False
        RIG.animation_data.action=None
        bpy.ops.export_scene.gltf(**{**options,"export_nla_strips":True})
        for track in RIG.animation_data.nla_tracks:track.mute=True
        meta=verify_glb(glb)
    names=[a.get("name") for a in meta.get("animations",[])]
    print("EXPORT_GLTF_SKINS",len(meta.get("skins",[])),flush=True)
    print("EXPORT_GLTF_ANIMATIONS",names,flush=True)
    print("EXPORT_GLTF_MESHES",len(meta.get("meshes",[])),flush=True)
    assert len(meta.get("skins",[]))>=1, "GLB lacks a rigged skin"
    assert len(meta.get("animations",[]))>=4, "GLB lacks all skeletal actions"
    assert len(meta.get("meshes",[]))>=30, "GLB lacks geometry"
    assert all(len(a.get("channels",[]))>0 for a in meta["animations"])
    assert os.path.getsize(path)>50000
    assert os.path.getsize(glb)>50000
    with open(os.path.join(OUT,"rig-animation-check.json"),"w") as f:
        json.dump({"skins":len(meta["skins"]),"animations":names,
                   "meshes":len(meta["meshes"]),
                   "deform_bones":len(RIG.data.bones),
                   "blender_objects":len(BODY)},f,indent=2)
    print("HUMAN_COMPLETED",len(BODY),len(RIG.data.bones),len(names),flush=True)

def stage_title(text):
    with open(os.path.join(OUT,"current-stage.txt"),"w") as f:f.write(text)

PHASES=[
("01 / ARMATURE",skeleton),
("02 / ORGANIC TORSO",body),
("03 / WALKABLE LEGS",legs),
("04 / DEFORMABLE ARMS + HANDS",arms),
("05 / SCULPTED FACE",face),
("06 / HAIR",hair),
("07 / CLOTHING DETAILS",details),
("08 / SKINNED ANIMATION ACTIONS",build_actions),
("09 / IDLE BREATHING",phase_idle),
("10 / WALKING LOOP",phase_walk),
("11 / RUNNING CYCLE",phase_run),
("12 / BOXING PUNCH",phase_punch),
]
setup()
stage_title("REAL BLENDER | Building rigged human")
if LIVE:
    progress={"index":0}
    def animate():
        global PREVIEW_FRAME
        if PREVIEW in ACTIONS:
            limit={"Idle_Breathing":96,"Walk_Loop":48,
                   "Run_Loop":32,"Punch_Right_Jab":48}[PREVIEW]
            PREVIEW_FRAME=(PREVIEW_FRAME%limit)+1
            bpy.context.scene.frame_set(PREVIEW_FRAME)
        return .10
    def advance():
        idx=progress["index"]
        if idx<len(PHASES):
            title,task=PHASES[idx]
            stage_title("KINETIC HUMAN | "+title)
            task()
            progress["index"]+=1
            for area in bpy.context.screen.areas:area.tag_redraw()
            if idx==8:bpy.app.timers.register(animate,first_interval=.10)
            return 4.5
        stage_title("EXPORTING RIGGED GLB + 4 ANIMATIONS")
        save()
        stage_title("COMPLETE | IDLE / WALK / RUN / PUNCH")
        return None
    bpy.app.timers.register(advance,first_interval=4.0)
    print("HUMAN_LIVE_MODE_STARTED",flush=True)
else:
    for title,func in PHASES:
        stage_title(title)
        func()
    save()
