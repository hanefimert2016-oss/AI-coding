import bpy, math, os, sys
from mathutils import Vector
out=sys.argv[sys.argv.index("--")+1]
os.makedirs(out,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def mat(n,c,metal=.65,emit=0):
 m=bpy.data.materials.new(n); m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get("Principled BSDF");p.inputs["Base Color"].default_value=(*c,1);p.inputs["Metallic"].default_value=metal;p.inputs["Roughness"].default_value=.27
 if emit:p.inputs["Emission Color"].default_value=(*c,1);p.inputs["Emission Strength"].default_value=emit
 return m
steel=mat("Brushed titanium",(.29,.36,.44)); dark=mat("Carbon fiber",(.025,.037,.052)); chrome=mat("Machined chrome",(.67,.76,.83),.95); cyan=mat("Cyan illuminated actuator",(.01,.75,1),.1,3); gold=mat("Hydraulic brass",(.83,.51,.16),.85); rubber=mat("Black elastomer",(.025,.025,.035),.1)
def part(n,loc,scale,material,kind='cube',bevel=.04):
 if kind=='cube':bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
 elif kind=='cylinder':bpy.ops.mesh.primitive_cylinder_add(vertices=48,location=loc)
 elif kind=='sphere':bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=loc)
 o=bpy.context.object;o.name=n;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 if bevel and kind!='sphere':b=o.modifiers.new("Precision rounded edges","BEVEL");b.width=bevel;b.segments=3;o.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
 return o
def rod(n,a,b,r,material):
 mid=(Vector(a)+Vector(b))/2;d=Vector(b)-Vector(a)
 o=part(n,mid,(r*2,r*2,d.length),material,'cylinder',.02);o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o
part("01 Foundation / industrial pedestal",(0,0,.16),(2.7,2.7,.32),dark)
part("02 Machined turntable",(0,0,.41),(1.55,1.55,.25),chrome,'cylinder')
part("03 Rotating bearing housing",(0,0,.68),(1.15,1.15,.35),steel,'cylinder')
part("04 Main vertical motor",(0,0,1.12),(.86,.86,.7),dark,'cylinder')
part("05 Cyan bearing ring",(0,0,1.5),(1.05,1.05,.1),cyan,'cylinder')
points=[(0,0,1.55),(.65,0,2.15),(1.25,0,3.5),(2.25,0,4.35),(3.22,0,4.45)]
for i,(a,b) in enumerate(zip(points[:-1],points[1:])):
 rod("Arm %02d central forged link"%i,a,b,.26 if i<2 else .18,steel)
 for side in (-1,1):
  shift=Vector((0,side*.24,0))
  rod("Arm %02d side truss %s"%(i,side),Vector(a)+shift,Vector(b)+shift,.085,chrome)
  rod("Arm %02d gold hydraulic %s"%(i,side),Vector(a)+shift+Vector((0,0,-.14)),Vector(b)+shift+Vector((0,0,-.14)),.048,gold)
 for j in range(3):
  t=(j+1)/4;center=Vector(a).lerp(Vector(b),t)
  part("Arm %02d armor plate %d"%(i,j),center,(.47,.64,.12),dark)
for i,p in enumerate(points[1:]):
 part("Joint %02d bearing"%i,p,(.67,.82,.67),chrome,'sphere')
 part("Joint %02d servo cap"%i,(p[0],p[1]+.46,p[2]),(.47,.13,.47),dark,'cylinder')
 part("Joint %02d LED status"%i,(p[0],p[1]-.47,p[2]),(.27,.12,.27),cyan,'sphere')
for side in (-1,1):
 rod("Gripper finger base %s"%side,(3.2,side*.22,4.45),(3.64,side*.30,4.36),.095,chrome)
 rod("Gripper articulated jaw %s"%side,(3.64,side*.30,4.36),(3.92,side*.17,4.24),.11,dark)
 part("Gripper rubber tip %s"%side,(3.93,side*.17,4.24),(.23,.17,.18),rubber)
for i in range(12):
 a=i*math.tau/12
 part("Base bolt %02d"%i,(1.08*math.cos(a),1.08*math.sin(a),.35),(.12,.12,.10),gold,'cylinder',.01)
# product studio
floor=part("Presentation floor",(0,0,-.18),(200,200,.2),dark)
world=bpy.context.scene.world;world.color=(.035,.035,.045)
for n,loc,power,size in [("Key",(-3,-4,8),2400,5),("Fill",(5,1,7),2000,5)]:
 l=bpy.data.lights.new(n,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=bpy.data.objects.new(n,l);bpy.context.collection.objects.link(o);o.location=loc
camera=bpy.data.cameras.new("Product camera");cam=bpy.data.objects.new("Product camera",camera);bpy.context.collection.objects.link(cam);cam.location=(8,-11,7);cam.rotation_euler=(Vector((1,0,2.5))-cam.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=7.7;bpy.context.scene.camera=cam
bpy.context.scene.render.engine='BLENDER_WORKBENCH';bpy.context.scene.display.shading.color_type='MATERIAL';bpy.context.scene.render.resolution_x=1280;bpy.context.scene.render.resolution_y=720;bpy.context.scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,"Titanium-Industrial-Robot-Arm.blend"))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='MESH' and o!=floor:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(out,"Titanium-Industrial-Robot-Arm.glb"),export_format='GLB',use_selection=True)
bpy.context.scene.render.filepath=os.path.join(out,"robot-arm-render.png");bpy.ops.render.render(write_still=True)
print("ROBOT_MODEL_DONE",len([o for o in bpy.context.scene.objects if o.type=='MESH']))
