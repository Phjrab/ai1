#!/usr/bin/env python3
"""Merge final Blender fallback with tested web foliage profiles; no dense foliage."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'realism_v2/material_fallback.json'
out=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'data/game-materials.json'
current=json.loads(out.read_text()) if out.exists() else {'materials':{}}
incoming=json.loads(source.read_text())
materials=current['materials'].copy()
for name,values in incoming['materials'].items():
    values=values.copy()
    if values.get('profile')=='original' and name in materials:
        values['profile']=materials[name]['profile']
    values['alphaMode']='OPAQUE'
    values['transmission']=0
    materials[name]=values
# Original native revision palette, shared with the dense render-only vegetation.
# Game retains its existing instanced mesh canopy and trunk geometry.
palette=[(.079,.146,.045),(.110,.184,.057),(.146,.224,.071),(.066,.127,.044),(.168,.240,.082),(.098,.166,.058)]
for name,values in materials.items():
    if name.startswith(('CAMPUS • canopy ', 'SITE • leaf ')):
        try:index=int(name.rsplit(' ',1)[1])
        except ValueError:continue
        values.update(profile='foliage',baseColorLinear=[*palette[index%len(palette)],1],roughness=.86,metalness=0,alphaMode='OPAQUE',transmission=0)
result={'version':'campus-realism-v2','colorSpace':'linear-sRGB','source':source.name,'notes':'Native material base PBR fallback; original lightweight instanced trees with realism-v2 foliage palette and smooth normals. Procedural Blender grain, dense leaves, translucent leaves and render-only bevels are not reproduced.','materials':dict(sorted(materials.items()))}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(f'{len(materials)} web material profiles written to {out}')
