import bpy,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from campus_materials import classify
for o in bpy.data.objects:
 if o.type=='MESH' and any(m and classify(m.name)=='foliage' for m in o.data.materials):print(o.name,len(o.data.vertices),len(o.data.polygons),[m.name if m else None for m in o.data.materials])
