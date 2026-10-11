"""Lossless .blend container recompression with exact decompressed-stream proof."""
from pathlib import Path
import zstandard as zstd,hashlib,json,time,resource
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'Chosun_Campus_Street_Lighting_v6.blend';target=path.with_suffix('.recompressed.blend');assert not target.exists()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
old_sha=file_sha(path);m=json.loads((ROOT/'lighting_manifest.json').read_text());assert old_sha==m['augmented_native_sha256'];start=time.time();old_stream=hashlib.sha256();count=0
with path.open('rb') as source,target.open('wb') as destination:
 with zstd.ZstdDecompressor().stream_reader(source,read_across_frames=True) as reader,zstd.ZstdCompressor(compression_params=zstd.ZstdCompressionParameters.from_level(10,window_log=27,enable_ldm=True)).stream_writer(destination,closefd=False) as writer:
  while block:=reader.read(1048576):old_stream.update(block);count+=len(block);writer.write(block)
new_stream=hashlib.sha256();new_count=0
with target.open('rb') as source,zstd.ZstdDecompressor().stream_reader(source,read_across_frames=True) as reader:
 while block:=reader.read(1048576):new_stream.update(block);new_count+=len(block)
assert count==new_count and old_stream.digest()==new_stream.digest()
new_sha=file_sha(target);old_bytes=path.stat().st_size;new_bytes=target.stat().st_size
archive=ROOT/'qa/native_smallwindow_container.blend';assert not archive.exists();path.rename(archive);target.rename(path)
proof={'status':'PASS','source_compressed_sha256':old_sha,'source_compressed_bytes':old_bytes,'final_native_sha256':new_sha,'final_native_bytes':new_bytes,'decompressed_stream_sha256':old_stream.hexdigest(),'decompressed_bytes':count,'exact_internal_bytes_preserved':True,'previous_proof_sha256':file_sha(ROOT/'qa/compression_initial/native_container_recompression.json'),'compression':'Zstandard level10,128MiB history window,long-distance matching, single thread','tool_sha256':file_sha(Path(__file__)),'seconds':time.time()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
report=ROOT/'qa/native_container_recompression.json';report.write_text(json.dumps(proof,indent=2)+'\n')
m['augmented_native_sha256']=new_sha;m['native_bytes']=new_bytes;m['native_container_recompression']={'report':'qa/native_container_recompression.json','sha256':file_sha(report),'source_native_sha256':old_sha,'exact_decompressed_stream_sha256':old_stream.hexdigest()};m['emitter_clearance_report_sha256']=file_sha(ROOT/'qa/emitter_clearance.json')
(ROOT/'lighting_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,indent=2))
