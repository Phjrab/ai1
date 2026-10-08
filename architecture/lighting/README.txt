CHOSUN CAMPUS — CONCEPTUAL TIME-OF-DAY STUDIES

These four native Blender renders use one model and precisely the same saved
07_Whole_Campus camera. Only illumination and a subset of glazing materials
change. Architecture geometry, roads, terrain and camera framing do not change.

The treatments are morning / noon / sunset / night; they are conceptual artistic
lighting conditions, not a dated solar-position analysis or a record of actual
operating hours, illuminated rooms or installed lighting performance.

Night uses selective warm window emission, gentle blue moonlit fill, and real
area lights beneath existing model lamp-head geometry. Window emission is not
sampled as a direct light source, which avoids excessive tiny-source noise at
this aerial scale. Local streetlight pools are directly computed by Cycles.
A very subtle native compositor fog-glow softens bright light points.

REPRODUCE
Blender 4.3.2, CPU Cycles. From the model delivery directory:
blender -b Chosun_Campus.blend -t 6 --python ../lighting/render_times.py -- morning time_of_day/01_Morning.png 2200 96
blender -b Chosun_Campus.blend -t 6 --python ../lighting/render_times.py -- noon time_of_day/02_Noon.png 2200 96
blender -b Chosun_Campus.blend -t 6 --python ../lighting/render_times.py -- sunset time_of_day/03_Sunset.png 2200 128
blender -b Chosun_Campus.blend -t 6 --python ../lighting/render_times.py -- night time_of_day/04_Night.png 2200 256

Each image has a companion JSON with source hash, camera and render metadata.
The script never saves changes into the architecture blend file.
