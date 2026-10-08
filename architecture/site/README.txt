CHOSUN UNIVERSITY MAIN BUILDING — PROCEDURAL CAMPUS SURROUNDINGS

Files
site.blend: standalone asset with one CHOSUN_SITE root collection, no camera/light.
site.glb: compact Y-up export, shared tree and vehicle meshes retained.
site_builder.py: original procedural script; import and call build_site() in Blender.
scene_stats.json: geometry sanity counts from successful build.
navigation.json: approximate navigation layout in Blender coordinates.
site_qa.png: isolated site inspection image, not a final architectural render.

Integration
Coordinate system is metres. Main front wall y=0, building grade z=0, building
length about 375m along x. Front is negative y. Site x=-235..235 and y=-140..123.
Append the CHOSUN_SITE collection into the building scene. build_site() adds a
new named collection, never clears existing objects. Standalone __main__ clears
the starter scene intentionally before saving the standalone site file.

Reference-grounded elements
Official university aerial gallery establishes wooded slopes immediately before
and behind the main building, narrow facade access road, straight central stair
axis, and the lower contour road. The 108 Stair photograph establishes the
central darker plaque strip, metal edge rails, wider bottom flight, and tree
lined approach. Official rear photograph establishes a narrow rear service lane
with parked vehicles at the uphill side.

Sources
https://dh.aks.ac.kr/~gwangju/asset/2022/ref/09_06.jpg
https://commons.wikimedia.org/wiki/File:Chosun_University_108_Stair.JPG
Reference evidence images reviewed in the separate chosun_site_refs folder.

Interpretive limitations
This is a visual architectural study, not a survey, engineering model, accurate
current parking inventory, or species inventory. All metric ground elevations,
road widths, curvature, lamp/bench locations, car count/placement, vegetation
species/count/positions, and stair run/rise are illustrative. The overall wooded
terrace relationship and main circulation axis are source-informed. Lower
campus buildings are outside this site's focused model scope. No source photo
is used as a texture or embedded in the mesh deliverable. All geometry and
materials are original, with fixed procedural seeds and shared asset meshes.
