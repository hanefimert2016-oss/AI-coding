#!/usr/bin/env python3
"""NOVA-01: original rigged adult human character with Idle, Walk, Run and Punch.
Fully procedural mesh authoring, armature skinning and real Blender animations.
The --live mode builds visible stages in an actual Blender desktop window.
"""
import bpy, math, os, sys
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
OUT=os.path.abspath(args[0] if args else "/tmp/nova")
LIVE="--live" in args
os.makedirs(OUT,exist_ok=True)
ARM=None
PARTS=[]
MATS={}
ACTION_MAP={}
STAGE=0

def mat(name,color,metal=0,rough=.55,emission=0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1)
    bs.inputs["Metallic"].default_value=metal
    bs.inputs["Roughness"].default_value=rough
    if emission:
        bs.inputs["Emission Color"].default_value=(*color,1)
        bs.inputs["Emission Strength"].default_value=emission
    return m

def objmesh(name,verts,faces,material,bone):
    mesh=bpy.data.meshes.new(name+" | topology")
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for poly in mesh.polygons:poly.use_smooth=True
    PARTS.append((obj,bone))
    return obj

def ball(name,at,scale,material,bone,segments=20,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=at)
    obj=bpy.context.object;obj.name=name
    obj.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:poly.use_smooth=True
    PARTS.append((obj,bone))
    return obj

def block(name,at,dimensions,material,bone,bevel=.014):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at)
    obj=bpy.context.object;obj.name=name
    obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod=obj.modifiers.new("Fabric curved corners","BEVEL")
        mod.width=bevel;mod.segments=3
        obj.modifiers.new("Weighted custom normals","WEIGHTED_NORMAL")
    PARTS.append((obj,bone))
    return obj

def tube(name,base,top,r0,r1,material,bone,segments=24,elliptical=1):
    a=Vector(base);b=Vector(top)
    direction=(b-a).normalized()
    arbitrary=Vector((0,1,0)) if abs(direction.y)<.93 else Vector((1,0,0))
    axisu=direction.cross(arbitrary).normalized()
    axisv=direction.cross(axisu).normalized()
    vs=[];fs=[]
    for i,(t,r) in enumerate([(0.0,r0*.78),(.10,r0),(.35,r0*.97),(.73,r1*1.04),(.96,r1),(1.0,r1*.79)]):
        pos=a.lerp(b,t)
        for j in range(segments):
            q=2*math.pi*j/segments
            pp=pos+axisu*math.cos(q)*r+axisv*math.sin(q)*r*elliptical
            vs.append(tuple(pp))
    fs.append(tuple(reversed(range(segments))))
    for i in range(5):
        for j in range(segments):
            a1=i*segments+j;b1=i*segments+(j+1)%segments
            fs.append((a1,b1,b1+segments,a1+segments))
    fs.append(tuple(range(5*segments,6*segments)))
    return objmesh(name,vs,fs,material,bone)

def loft(name,layers,material,bone,segments=32):
    verts=[];faces=[]
    for z,rx,ry,offy in layers:
        for i in range(segments):
            a=i*math.tau/segments
            verts.append((math.cos(a)*rx,offy+math.sin(a)*ry,z))
    faces.append(tuple(reversed(range(segments))))
    for ring in range(len(layers)-1):
        for j in range(segments):
            a=ring*segments+j;b=ring*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    faces.append(tuple(range((len(layers)-1)*segments,len(layers)*segments)))
    return objmesh(name,verts,faces,material,bone)

def stage(idx,title):
    global STAGE
    STAGE=idx
    label="STAGE %02d / 10 — %s"%(idx,title)
    with open(os.path.join(OUT,"current-stage.txt"),"w") as fp:fp.write(label)
    print("HUMAN_STAGE",idx,title,"PARTS",len(PARTS),flush=True)
    if LIVE:
        for screen in bpy.data.screens:
            for area in screen.areas:area.tag_redraw()

def setup():
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    MATS.update({
        "skin":mat("Skin | warm natural umber",(.56,.30,.19),rough=.75),
        "skin_lit":mat("Skin | subtle facial highlight",(.66,.39,.26),rough=.66),
        "hair":mat("Hair | dark espresso",(.062,.035,.03),rough=.80),
        "hair_bright":mat("Hair | mahogany strands",(.14,.068,.042),rough=.78),
        "eyewhite":mat("Eyes | sclera",(.88,.91,.92),rough=.28),
        "iris":mat("Eyes | teal iris",(.06,.30,.32),rough=.23),
        "pupil":mat("Eyes | pupils",(.005,.015,.020),rough=.20),
        "jacket":mat("Jacket | technical midnight graphite",(.079,.16,.22),rough=.62),
        "jacketpanel":mat("Jacket | teal geometric seam",(.065,.24,.30),rough=.60),
        "shirt":mat("Inner t-shirt | offwhite",(.77,.78,.72),rough=.85),
        "pants":mat("Pants | charcoal denim",(.074,.095,.13),rough=.84),
        "pantslight":mat("Pants | faded stitching",(.15,.18,.20),rough=.83),
        "boots":mat("Boots | dark carbon leather",(.024,.028,.042),rough=.42),
        "sole":mat("Boots | rubber sole",(.11,.12,.13),rough=.89),
        "metal":mat("Clothing | satin metal",(.45,.60,.64),metal=.77,rough=.25),
        "cyan":mat("Technology | luminous mint",(.07,.69,.82),metal=.1,rough=.4,emission=1.4),
        "studio":mat("Studio | slate backdrop",(.049,.070,.105),rough=.80),
    })
    scene=bpy.context.scene
    scene.render.engine="BLENDER_WORKBENCH"
    scene.render.resolution_x=1600
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.unit_settings.system="METRIC"
    scene.render.film_transparent=False
    scene.world.color=(.042,.050,.068)
    cam_data=bpy.data.cameras.new("Portrait framing | 85 mm")
    cam=bpy.data.objects.new("STUDIO CAMERA",cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location=(3.4,-5.8,2.55)
    cam.rotation_euler=(Vector((0,0,1.07))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam_data.type="ORTHO";cam_data.ortho_scale=2.65
    scene.camera=cam
    for name,xyz,power,rgb,size in [
        ("Key softbox",(-3,-4,5),1700,(.72,.88,1),3.8),
        ("Amber rim",(3,2,4),1600,(1,.75,.54),3.1),
        ("Front fill",(2,-3,3),900,(.72,.9,1),2.5)]:
        light=bpy.data.lights.new(name,"AREA")
        light.energy=power;light.color=rgb;light.shape="DISK";light.size=size
        ob=bpy.data.objects.new(name,light)
        bpy.context.collection.objects.link(ob)
        ob.location=xyz
    # Studio ground deliberately excludes the GLB export
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.075))
    floor=bpy.context.object;floor.name="STUDIO GROUND — not included in GLB"
    floor.dimensions=(100,100,.14)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    floor.data.materials.append(MATS["studio"])
    if LIVE:
        for a in bpy.context.screen.areas:
            if a.type=="VIEW_3D":
                s=a.spaces.active
                s.region_3d.view_perspective="CAMERA"
                s.region_3d.view_camera_zoom=2
                s.shading.type="SOLID"
                s.shading.color_type="MATERIAL"
                s.shading.show_cavity=True
                s.shading.cavity_type="BOTH"
                s.overlay.show_floor=False
                s.overlay.show_axis_x=False
                s.overlay.show_axis_y=False
    stage(1,"STUDIO AND HUMAN ANATOMY")

def make_skeleton():
    global ARM
    bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0))
    ARM=bpy.context.object
    ARM.name="NOVA / 22-Bone Motion Skeleton"
    ARM.show_in_front=True
    ARM.data.display_type="STICK"
    ARM.data.name="NOVA / anatomically named skeleton"
    old=list(ARM.data.edit_bones)
    for b in old:ARM.data.edit_bones.remove(b)
    definitions=[
        ("root",(0,0,0),(0,0,.19),None),
        ("hips",(0,0,1.00),(0,0,1.18),"root"),
        ("spine",(0,0,1.16),(0,0,1.44),"hips"),
        ("chest",(0,0,1.43),(0,0,1.69),"spine"),
        ("neck",(0,0,1.68),(0,0,1.79),"chest"),
        ("head",(0,0,1.78),(0,0,2.02),"neck"),
    ]
    for side in (-1,1):
        label="L" if side==1 else "R"
        x=lambda n:side*n
        definitions.extend([
            ("clavicle."+label,(x(.09),0,1.62),(x(.26),0,1.60),"chest"),
            ("upper_arm."+label,(x(.26),0,1.60),(x(.50),0,1.33),"clavicle."+label),
            ("forearm."+label,(x(.50),0,1.33),(x(.68),0,1.08),"upper_arm."+label),
            ("hand."+label,(x(.68),0,1.08),(x(.75),0,1.00),"forearm."+label),
            ("thigh."+label,(x(.13),0,1.04),(x(.15),0,.60),"hips"),
            ("shin."+label,(x(.15),0,.60),(x(.16),0,.15),"thigh."+label),
            ("foot."+label,(x(.16),0,.15),(x(.16),-.16,.09),"shin."+label),
            ("toe."+label,(x(.16),-.16,.09),(x(.16),-.28,.085),"foot."+label),
        ])
    bones={}
    for name,start,end,parent in definitions:
        b=ARM.data.edit_bones.new(name)
        b.head=start;b.tail=end
        bones[name]=b
        b.use_deform=True
        if parent:b.parent=bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose in ARM.pose.bones:pose.rotation_mode="XYZ"
    stage(2,"22-BONE ARMATURE / SKELETON")

def body():
    loft("Sculpted anatomical torso",[
        (1.13,.17,.105,-.002),(1.18,.21,.11,0),
        (1.31,.20,.105,0),(1.43,.248,.133,0),
        (1.55,.29,.158,0),(1.62,.27,.14,0),
        (1.69,.15,.09,0)],MATS["jacket"],"chest")
    loft("Tapered hip and pelvis",[
        (.99,.156,.115,0),(1.045,.225,.132,0),
        (1.115,.235,.142,0),(1.18,.18,.11,0)],
        MATS["pants"],"hips")
    loft("Inner undershirt neckline",[
        (1.63,.11,.09,-.002),(1.70,.102,.085,0),
        (1.73,.081,.074,0)],MATS["shirt"],"chest")
    loft("Neck above jacket collar",[
        (1.69,.078,.077,0),(1.78,.079,.074,0)],MATS["skin"],"neck")
    block("Front shirt / decorative zipper",(.0,-.157,1.46),(.018,.012,.37),
          MATS["metal"],"chest",.003)
    for sign in (-1,1):
        x=.22*sign
        ball("Raised shoulder deltoid %s"%sign,(x,0,1.57),
             (.116,.130,.12),MATS["jacket"],"chest")
        block("Jacket chest color insert %s"%sign,(sign*.106,-.159,1.50),
              (.12,.01,.12),MATS["jacketpanel"],"chest",.01)
        block("Jacket pocket %s"%sign,(sign*.113,-.125,1.29),
              (.14,.018,.075),MATS["jacketpanel"],"chest",.01)
    block("Belt technical buckle",(0,-.142,1.08),(.095,.026,.057),
          MATS["metal"],"hips",.01)
    stage(3,"DETAILED HUMAN TORSO / CLOTHING")

def head_face():
    ball("Skull / proportional cranium",(0,0,1.863),(.117,.109,.160),MATS["skin"],"head",32,20)
    ball("Jaw and chin",(0,-.023,1.80),(.094,.087,.083),MATS["skin"],"head")
    ball("Nose bridge",(0,-.117,1.864),(.024,.030,.056),MATS["skin_lit"],"head")
    ball("Nose tip",(0,-.139,1.835),(.027,.031,.023),MATS["skin"],"head")
    for sign in (-1,1):
        side="L" if sign>0 else "R"
        ball("External ear "+side,(sign*.114,0,1.866),(.025,.024,.046),MATS["skin"],"head")
        ball("Eye white "+side,(sign*.051,-.092,1.892),(.034,.016,.025),MATS["eyewhite"],"head")
        ball("Iris "+side,(sign*.050,-.107,1.890),(.015,.008,.015),MATS["iris"],"head")
        ball("Pupil "+side,(sign*.050,-.113,1.891),(.007,.005,.009),MATS["pupil"],"head")
        block("Eyebrow "+side,(sign*.054,-.103,1.927),
              (.063,.012,.011),MATS["hair"],"head",.004, )
        ball("Cheek volume "+side,(sign*.068,-.069,1.820),
             (.051,.050,.047),MATS["skin_lit"],"head")
    block("Mouth upper lip",(0,-.108,1.789),(.057,.011,.007),
          MATS["skin_lit"],"head",.003)
    # A layered swept haircut rather than a generic sphere.
    ball("Main side-parted cropped hair cap",(0,.006,1.969),
         (.123,.115,.086),MATS["hair"],"head",32,16)
    for sign in (-1,1):
        ball("Side fade "+str(sign),(sign*.092,.025,1.944),
             (.032,.071,.064),MATS["hair"],"head")
    for n in range(9):
        x=-.093+n*.022
        z=1.995+.013*math.sin(n*.62)
        ball("Individually sculpted hair lock %02d"%n,(x,-.077,z),
             (.026,.039,.029),MATS["hair_bright"] if n%4==0 else MATS["hair"],"head")
    stage(4,"FACE / HAIR / EYES / EXPRESSIONS")

def limbs():
    for sign in (-1,1):
        label="L" if sign>0 else "R"
        def p(x,z,y=0):return (sign*x,y,z)
        tube("Upper arm jacket / "+label,p(.26,1.59),p(.50,1.33),.100,.078,
             MATS["jacket"],"upper_arm."+label)
        tube("Jacket cuff / "+label,p(.489,1.355),p(.515,1.302),.081,.076,
             MATS["jacketpanel"],"upper_arm."+label)
        ball("Soft elbow connector / "+label,p(.50,1.32),(.071,.073,.071),
             MATS["jacket"],"forearm."+label)
        tube("Technical forearm sleeve / "+label,p(.51,1.31),p(.68,1.092),
             .082,.059,MATS["jacket"],"forearm."+label)
        tube("Wrist skin / "+label,p(.67,1.102),p(.73,1.038),
             .052,.044,MATS["skin"],"hand."+label,20)
        ball("Hand palm / "+label,p(.745,1.013),
             (.060,.041,.073),MATS["skin"],"hand."+label)
        for finger in range(4):
            fx=.739+finger*.014
            tube("Hand finger "+label+" "+str(finger),
                 p(fx,1.006,-.018+finger*.010),
                 p(fx+.011,.950,-.018+finger*.010),
                 .010,.007,MATS["skin"],"hand."+label,10)
        tube("Thumb "+label,p(.704,1.036,-.029),p(.688,.994,-.05),
             .016,.009,MATS["skin"],"hand."+label,12)
        tube("Anatomical thigh / denim "+label,p(.13,1.01),p(.15,.61),
             .142,.103,MATS["pants"],"thigh."+label,32,1.05)
        ball("Kneecap / tailored trouser "+label,p(.15,.605),
             (.111,.107,.095),MATS["pants"],"shin."+label)
        tube("Shin / tapered denim "+label,p(.15,.589),p(.16,.148),
             .104,.076,MATS["pants"],"shin."+label,32,1.08)
        tube("Sock heel "+label,p(.159,.181),p(.16,.119),
             .070,.065,MATS["pantslight"],"shin."+label)
        block("Boot leather ankle "+label,p(.16,.127,-.012),
              (.175,.195,.181),MATS["boots"],"foot."+label,.040)
        block("Sneaker toe cap "+label,p(.16,.071,-.15),
              (.185,.302,.098),MATS["boots"],"foot."+label,.037)
        block("Rubber outsole "+label,p(.16,.045,-.126),
              (.206,.32,.046),MATS["sole"],"foot."+label,.016)
        for s in range(4):
            block("Shoe lacing "+label+" "+str(s),
                 p(.16,.138,-.052-s*.025),(.09,.011,.009),
                 MATS["metal"],"foot."+label,.004)
        # decorative seams on jacket sleeve
        ball("Elbow protective seam "+label,p(.515,1.304),
             (.084,.083,.017),MATS["jacketpanel"],"forearm."+label)
    stage(5,"SCULPTED ARMS / HANDS / LEGS / FOOTWEAR")

def finishes():
    for sign in (-1,1):
        label="L" if sign>0 else "R"
        for i in range(4):
            tube("Side trouser stitching "+label+" "+str(i),
              (sign*.255,0,1.00-i*.084),
              (sign*.255,0,.945-i*.084),
              .003,.003,MATS["pantslight"],"thigh."+label,8)
        for i in range(3):
            block("Shoulder reflective tape "+label+" "+str(i),
                  (sign*(.260+i*.015),-.1,1.58-i*.04),
                  (.013,.008,.028),MATS["cyan"],"upper_arm."+label,.003)
        ball("Glowing wrist wearable "+label,(sign*.678,-.058,1.100),
             (.027,.013,.014),MATS["cyan"],"forearm."+label)
    stage(6,"GARMENT STITCHING / ACCESSORY DETAIL")

def skin_to_bones():
    assert ARM is not None
    for o,bone in PARTS:
        group=o.vertex_groups.new(name=bone)
        group.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
        o.parent=ARM
        modifier=o.modifiers.new("NOVA skeletal deformation","ARMATURE")
        modifier.object=ARM
        modifier.use_vertex_groups=True
        modifier.use_bone_envelopes=False
    stage(7,"SKIN WEIGHTS / BONE BINDING / IK-READY RIG")

def neutral():
    for pb in ARM.pose.bones:
        pb.rotation_mode="XYZ"
        pb.rotation_euler=(0,0,0)
        pb.location=(0,0,0)
        pb.scale=(1,1,1)

def animate():
    assert ARM is not None
    scene=bpy.context.scene
    scene.render.fps=30
    ARM.animation_data_create()
    def clip(name,frames,fn):
        neutral()
        action=bpy.data.actions.new("NOVA / "+name)
        action.use_fake_user=True
        ARM.animation_data.action=action
        for f in frames:
            scene.frame_set(f)
            neutral()
            fn(f)
            for pb in ARM.pose.bones:
                pb.keyframe_insert(data_path="rotation_euler",frame=f,group=pb.name)
                if pb.name in ("hips","root"):
                    pb.keyframe_insert(data_path="location",frame=f,group=pb.name)
        ARM.animation_data.action=None
        ACTION_MAP[name]=action
        track=ARM.animation_data.nla_tracks.new()
        track.name=name
        strip=track.strips.new(name,1,action)
        strip.blend_type="REPLACE"
        strip.extrapolation="NOTHING"
        print("CREATED_ACTION",name,"frames",frames[-1],"curves",len(action.fcurves),flush=True)
    def idle(frame):
        q=2*math.pi*(frame-1)/48
        ARM.pose.bones["chest"].rotation_euler.y=.016*math.sin(q)
        ARM.pose.bones["head"].rotation_euler.y=.018*math.sin(q*.5)
        ARM.pose.bones["hips"].location.z=.013*math.sin(q)
        for side in ("L","R"):
            ARM.pose.bones["upper_arm."+side].rotation_euler.x=.03*math.sin(q)
    clip("Idle",[1,7,13,19,25,31,37,43,49],idle)
    def walk(frame):
        q=2*math.pi*(frame-1)/24
        ARM.pose.bones["hips"].location.z=.027*math.sin(2*q)
        ARM.pose.bones["chest"].rotation_euler.y=.045*math.sin(q)
        for side,offset in (("L",0),("R",math.pi)):
            phase=q+offset
            swing=math.sin(phase)
            ARM.pose.bones["thigh."+side].rotation_euler.x=.42*swing
            ARM.pose.bones["shin."+side].rotation_euler.x=.05+.43*max(0,-swing)
            ARM.pose.bones["foot."+side].rotation_euler.x=-.12*swing
            ARM.pose.bones["upper_arm."+side].rotation_euler.x=-.32*swing
            ARM.pose.bones["forearm."+side].rotation_euler.x=.20
    clip("Walk",list(range(1,26,2)),walk)
    def run(frame):
        q=2*math.pi*(frame-1)/18
        ARM.pose.bones["hips"].location.z=.06+.06*math.sin(q*2)
        ARM.pose.bones["chest"].rotation_euler.x=.13
        ARM.pose.bones["head"].rotation_euler.x=-.08
        for side,offset in (("L",0),("R",math.pi)):
            swing=math.sin(q+offset)
            ARM.pose.bones["thigh."+side].rotation_euler.x=.75*swing
            ARM.pose.bones["shin."+side].rotation_euler.x=.12+.7*max(0,-swing)
            ARM.pose.bones["foot."+side].rotation_euler.x=-.24*swing
            ARM.pose.bones["upper_arm."+side].rotation_euler.x=-.57*swing
            ARM.pose.bones["forearm."+side].rotation_euler.x=.67
    clip("Run",list(range(1,20)),run)
    def punch(frame):
        t=(frame-1)/32
        # Sharp right-handed lead punch, recoil and guarded stance.
        reach=(math.sin(min(t,1)*math.pi))**4
        ARM.pose.bones["chest"].rotation_euler.z=-.18*reach
        ARM.pose.bones["hips"].rotation_euler.z=.09*reach
        ARM.pose.bones["upper_arm.R"].rotation_euler.x=-.90*reach
        ARM.pose.bones["upper_arm.R"].rotation_euler.z=-.44*reach
        ARM.pose.bones["forearm.R"].rotation_euler.x=.72*reach
        ARM.pose.bones["upper_arm.L"].rotation_euler.x=-.30*reach
        ARM.pose.bones["forearm.L"].rotation_euler.x=.55*reach
        ARM.pose.bones["head"].rotation_euler.z=.09*reach
    clip("Punch",[1,5,9,12,15,18,22,26,29,33],punch)
    neutral()
    scene.frame_set(1)
    stage(8,"FOUR KEYFRAMED MOTION CLIPS / IDLE WALK RUN PUNCH")

def export():
    outblend=os.path.join(OUT,"NOVA-01-Rigged-Human-Animated.blend")
    outglb=os.path.join(OUT,"NOVA-01-Rigged-Human-4-Animations.glb")
    bpy.ops.object.select_all(action="DESELECT")
    ARM.select_set(True)
    for ob,_ in PARTS:ob.select_set(True)
    bpy.context.view_layer.objects.active=ARM
    bpy.ops.wm.save_as_mainfile(filepath=outblend)
    props=set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs=dict(filepath=outglb,export_format="GLB",use_selection=True,
        export_animations=True,export_skins=True,export_force_sampling=True,
        export_materials="EXPORT")
    if "export_animation_mode" in props:
        kwargs["export_animation_mode"]="NLA_TRACKS"
    if "export_nla_strips" in props:
        kwargs["export_nla_strips"]=True
    print("GLB_EXPORT_ARGS",kwargs,flush=True)
    bpy.ops.export_scene.gltf(**kwargs)
    assert os.path.getsize(outblend)>20000 and os.path.getsize(outglb)>20000
    print("NOVA_GLTF_EXPORTED",outglb,os.path.getsize(outglb),flush=True)
    print("NOVA_BLEND_SAVED",outblend,os.path.getsize(outblend),flush=True)
    print("NOVA_CHARACTER_COMPLETE","SKIN_MESHES",len(PARTS),
          "BONES",len(ARM.data.bones),"CLIPS",list(ACTION_MAP),flush=True)
    stage(9,"BLEND / GLB / FOUR ANIMATIONS SAVED")

def playback():
    if not LIVE:return
    stage(10,"ANIMATION PLAYBACK IN BLENDER")
    # Temporarily unmute individual NLA tracks in sequence on the live stage,
    # so the screen recording contains actual moving animation previews.
    tracks=list(ARM.animation_data.nla_tracks)
    for t in tracks:t.mute=True
    state={"i":0}
    def next_clip():
        if state["i"]>=4:
            for t in tracks:t.mute=False
            bpy.ops.screen.animation_cancel(restore_frame=False)
            stage(10,"ANIMATION SHOWCASE COMPLETE")
            return None
        for t in tracks:t.mute=True
        current=tracks[state["i"]]
        current.mute=False
        bpy.context.scene.frame_start=1
        bpy.context.scene.frame_end=ACTION_MAP[current.name].frame_range[1]
        bpy.context.scene.frame_set(1)
        with open(os.path.join(OUT,"current-stage.txt"),"w") as f:
            f.write("ANIMATION %d / 4       %s"%(state["i"]+1,current.name.upper()))
        try:
            bpy.ops.screen.animation_play()
        except Exception:
            print("Animation preview unable to auto-play",flush=True)
        state["i"]+=1
        return 5.0
    bpy.app.timers.register(next_clip,first_interval=2.0)

PHASES=[setup,make_skeleton,body,head_face,limbs,finishes,skin_to_bones,animate,export,playback]
if LIVE:
    counter={"i":0}
    def stage_timer():
        i=counter["i"]
        if i>=len(PHASES):return None
        PHASES[i]()
        counter["i"]+=1
        return 4.0 if i<8 else 1.0
    bpy.app.timers.register(stage_timer,first_interval=5)
    print("NOVA_LIVE_CHARACTER_CONSTRUCTION_STARTED",flush=True)
else:
    for f in PHASES:f()
