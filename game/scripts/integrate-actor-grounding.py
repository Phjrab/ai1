#!/usr/bin/env python3
"""Seed existing actor heights from the final native support at unchanged XY."""
import argparse,hashlib,json,math
from pathlib import Path

def apply(root,source):
    raw=source.read_bytes();data=json.loads(raw)
    assert data['schema']=='actor_grounding_v5' and data['version']==1
    assert hashlib.sha256((root/'data/grade-sync-baseline.json').read_bytes()).hexdigest()==data['source_baseline_sha256'],'Actor source baseline differs from native-bound input'
    wp=root/'dist/world-config.js';text=wp.read_text();world=json.loads(text.split('export const WORLD = ')[1].rstrip(';\n'))
    expected={(kind,index):[p['position'][0],-p['position'][2]] for kind in ['extraNPCs','extraCars'] for index,p in enumerate(world[kind])}
    expected.update({('baseCars',0):[8,-20],('baseCars',1):[-58,-21]})
    seen=set();updates=[];base=[None,None]
    for record in data['actors']:
        key=(record['kind'],record['index']);assert key in expected and key not in seen,'Unknown or duplicate actor grounding record'
        xy=record['positionXY'];assert len(xy)==2 and all(math.isfinite(v) for v in xy)
        assert math.dist(xy,expected[key])<.00001,'Actor grounding changed an existing XY position'
        z=record['floor_z'];assert math.isfinite(z) and record['support_object'],'Final support height/object required'
        if key[0]=='baseCars':base[key[1]]=z
        else:world[key[0]][key[1]]['position'][1]=z
        updates.append({'kind':key[0],'index':key[1],'floor_z':z,'support_object':record['support_object']});seen.add(key)
    assert seen==set(expected),'Every existing actor spawn needs a final support record'
    world['baseCarGroundHeights']=base
    report={'sourceSha256':hashlib.sha256(raw).hexdigest(),'updated':updates,'xyChanged':False,'finalGLBSupportVerification':'pending'}
    wp.write_text(text.split('\n')[0]+'\nexport const WORLD = '+json.dumps(world,ensure_ascii=False,separators=(',',':'))+';\n')
    (root/'data/actor-grounding.json').write_bytes(raw);(root/'data/actor-grounding-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--game-root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();print(json.dumps(apply(args.game_root,args.source)))
