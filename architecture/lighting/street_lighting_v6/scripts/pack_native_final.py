"""Lossless single-step compression of the freshly saved native container."""
from pathlib import Path
import zstandard as zstd,hashlib,json,time,resource
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'Chosun_Campus_Street_Lighting_v6.blend';temporary=path.with_suffix('.packed.blend');assert not temporary.exists()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
m=json.loads((ROOT/'lighting_manifest.json').read_text());old_sha=sha(path);assert m['augmented_native_sha256']==old_sha;start=time.time();h=hashlib.sha256();count=0
params=zstd.ZstdCompressionParameters.from_level(10,window_log=27,enable_ldm=True)
with path.open('rb') as f,temporary.open('wb') as o:
 with zstd.ZstdDecompressor().stream_reader(f,read_across_frames=True) as reader,zstd.ZstdCompressor(compression_params=params).stream_writer(o,closefd=False) as writer:
  while block:=reader.read(1048576):h.update(block);count+=len(block);writer.write(block)
check=hashlib.sha256();check_n=0
with temporary.open('rb') as f,zstd.ZstdDecompressor().stream_reader(f,read_across_frames=True) as reader:
 while block:=reader.read(1048576):check.update(block);check_n+=len(block)
assert count==check_n and h.digest()==check.digest()
new_sha=sha(temporary);old_n=path.stat().st_size;new_n=temporary.stat().st_size
archive=ROOT/'qa/native_save_output.blend';assert not archive.exists();path.rename(archive);temporary.rename(path)
record={'status':'PASS','source_compressed_sha256':old_sha,'source_compressed_bytes':old_n,'source_saved_container':'qa/native_save_output.blend','final_native_sha256':new_sha,'final_native_bytes':new_n,'decompressed_stream_sha256':h.hexdigest(),'decompressed_bytes':count,'exact_internal_bytes_preserved':True,'compression':'Zstandard level10,128MiB history,long-distance matching,single thread','tool_sha256':sha(Path(__file__)),'seconds':time.time()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
report=ROOT/'qa/native_final_container.json';report.write_text(json.dumps(record,indent=2)+'\n');m['augmented_native_sha256']=new_sha;m['native_bytes']=new_n;m['native_container_recompression']={'report':'qa/native_final_container.json','sha256':sha(report),'source_saved_container_sha256':old_sha,'exact_decompressed_stream_sha256':h.hexdigest()};m['emitter_clearance_report_sha256']=sha(ROOT/'qa/emitter_clearance.json')
(ROOT/'lighting_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,indent=2))
