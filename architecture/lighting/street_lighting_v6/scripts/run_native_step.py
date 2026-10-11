"""One guarded native operation; never close or alter other processes."""
import argparse,subprocess,time,json,hashlib,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLENDER=Path('/usr/bin/blender');BASE=ROOT.parent/'inputs/Chosun_Campus_Realism_v2.blend'
def available():return next(int(x.split()[1])/1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
p=argparse.ArgumentParser();p.add_argument('step',choices=['build','reopen','evening','night','detail']);p.add_argument('--run-id',default='01');a=p.parse_args()
assert available()>=5600,'Need at least5600MiB available before starting.'
if a.step=='build':native=BASE;script=ROOT/'scripts/build_lighting_revision.py';args=[]
elif a.step=='reopen':native=ROOT/'Chosun_Campus_Street_Lighting_v6.blend';script=ROOT/'scripts/verify_native_reopen.py';args=[]
else:native=ROOT/'Chosun_Campus_Street_Lighting_v6.blend';script=ROOT/'scripts/render_lighting_revision.py';args=['--','--view',a.step]
threads='8' if a.step in {'evening','night','detail'} else '4'
cmd=[str(BLENDER),'--background',str(native),'--disable-autoexec','--threads',threads,'--python-exit-code','1','--python',str(script),*args]
log=ROOT/'qa'/('native_'+a.step+'_'+a.run_id+'.log');assert not log.exists()
start=time.time();minimum=available();aborted=False
with log.open('w') as f:
 child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT)
 while child.poll() is None:
  now=available();minimum=min(minimum,now)
  if now<1250:aborted=True;child.terminate();break
  time.sleep(.1)
 code=child.wait()
report={'status':'PASS' if code==0 and not aborted else 'FAIL','step':a.step,'command':cmd,'seconds':time.time()-start,'minimum_available_mib':minimum,'aborted_for_memory':aborted,'exit_code':code,'peak_child_rss_mib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024,'other_processes_touched':False}
(ROOT/'qa'/('native_'+a.step+'_'+a.run_id+'_execution.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='PASS' else 1)
