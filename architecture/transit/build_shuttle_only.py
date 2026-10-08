from pathlib import Path
p=Path(__file__).parent
src=(p/'build_transit.py').read_text().split('# Photographed 2021 shelter:')[0]
exec(compile(src,str(p/'build_transit.py'),'exec'))
bpy.ops.wm.save_as_mainfile(filepath=str(p/'shuttle_livery.blend'))
