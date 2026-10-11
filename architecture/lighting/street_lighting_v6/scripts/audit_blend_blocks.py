"""Stream native .blend BHead inventories without Blender or native mutations.

Reads plain, gzip, or Zstandard Blender files in bounded chunks. Maps SDNA block
indices to their native types and records payload counts/bytes. Verifies whether
all bytes in each native type are zero, useful for identifying all-empty
MDeformVert storage. It never follows native pointers or rewrites input files. When Blender's Python
lacks zstandard, the same script streams the audit in installed system python3;
only the compact JSON report crosses the subprocess boundary.

python audit_blend_blocks.py OUTPUT.json ORIGINAL.blend REVISED.blend
"""
from pathlib import Path
from collections import defaultdict
import gzip
import hashlib
import json
import struct
import shutil
import subprocess
import sys
import time


def _open(path):
    raw=Path(path).open('rb');magic=raw.read(4);raw.seek(0)
    if magic==b'\x28\xb5\x2f\xfd':
        try:
            import zstandard
        except ModuleNotFoundError:
            raw.close()
            raise
        return zstandard.ZstdDecompressor().stream_reader(raw,read_across_frames=True)
    if magic[:2]==b'\x1f\x8b':return gzip.GzipFile(fileobj=raw)
    return raw


def _read_exact(stream,n):
    parts=[]
    while n:
        data=stream.read(n)
        if not data:raise ValueError('Unexpected end of Blender stream')
        parts.append(data);n-=len(data)
    return b''.join(parts)


def _dna_names(data,endian):
    i=0
    def tag(expected):
        nonlocal i
        assert data[i:i+4]==expected,(i,expected,data[i:i+4]);i+=4
    def number():
        nonlocal i
        value=struct.unpack_from(endian+'I',data,i)[0];i+=4;return value
    def strings(count):
        nonlocal i
        out=[]
        for _ in range(count):
            end=data.index(b'\0',i);out.append(data[i:end].decode('ascii'));i=end+1
        i=(i+3)&~3;return out
    tag(b'SDNA');tag(b'NAME');names=strings(number());tag(b'TYPE');types=strings(number())
    tag(b'TLEN');lengths=struct.unpack_from(endian+str(len(types))+'H',data,i);i+=len(types)*2;i=(i+3)&~3
    tag(b'STRC');count=number();result=[]
    for _ in range(count):
        ti,n=struct.unpack_from(endian+'HH',data,i);i+=4
        result.append({'name':types[ti],'size':lengths[ti]});i+=4*n
    return result


def _system_inventory(path):
    # Blender's embedded Python need not provide zstandard. Use only the already
    # installed system interpreter; the same audited script performs the same
    # bounded-memory decompression and BHead/SDNA inspection in that process.
    interpreter=shutil.which('python3')
    if not interpreter:
        raise RuntimeError('zstandard is missing and no system python3 is available')
    command=[interpreter,str(Path(__file__).resolve()),'--inventory-stdout',str(Path(path).resolve())]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=120)
    if result.returncode:
        raise RuntimeError('System Python native-block inventory failed: '+result.stderr[-2000:])
    report=json.loads(result.stdout)
    report['reader_backend']='installed_system_python_zstandard_subprocess'
    report['requested_reader_executable']=str(Path(interpreter).resolve())
    return report


def inventory(path, *, allow_system_fallback=True):
    start=time.monotonic();stats=defaultdict(lambda:{'blocks':0,'items':0,'payload_bytes':0,'all_payload_bytes_zero':True})
    decompressed_bytes=0;stream_sha=hashlib.sha256();dna=None
    try:
        reader=_open(path)
    except ModuleNotFoundError as exc:
        if exc.name!='zstandard' or not allow_system_fallback:
            raise
        return _system_inventory(path)
    with reader as stream:
        header=_read_exact(stream,12);stream_sha.update(header);decompressed_bytes+=12
        if header[:7]!=b'BLENDER':raise ValueError('Not a Blender stream')
        endian='<' if header[8:9]==b'v' else '>';pointer_size=8 if header[7:8]==b'-' else 4
        format=endian+('4sIQII' if pointer_size==8 else '4sIIII');size=struct.calcsize(format)
        while True:
            bhead=stream.read(size)
            if not bhead:break
            if len(bhead)!=size:raise ValueError('Truncated Blender block header')
            stream_sha.update(bhead);decompressed_bytes+=size
            code,length,address,sdna,count=struct.unpack(format,bhead)
            record=stats[sdna];record['blocks']+=1;record['items']+=count;record['payload_bytes']+=length
            dna_parts=[];remaining=length
            while remaining:
                chunk=_read_exact(stream,min(remaining,1024*1024));stream_sha.update(chunk);decompressed_bytes+=len(chunk);remaining-=len(chunk)
                # bytes.count executes in native code with no Python per-byte loop.
                if record['all_payload_bytes_zero'] and chunk.count(0)!=len(chunk):record['all_payload_bytes_zero']=False
                if code==b'DNA1':dna_parts.append(chunk)
            if code==b'DNA1':dna=_dna_names(b''.join(dna_parts),endian)
            if code.startswith(b'ENDB'):break
    if dna is None:raise ValueError('Missing DNA1 schema')
    mapped={}
    for index,record in stats.items():
        name=dna[index]['name'] if index<len(dna) else 'unknown_sdna_'+str(index)
        mapped[name]={**record,'struct_size':dna[index]['size'] if index<len(dna) else None}
    return {'path':str(Path(path).resolve()),'decompressed_bytes':decompressed_bytes,'decompressed_sha256':stream_sha.hexdigest(),
            'native_types':mapped,'seconds':round(time.monotonic()-start,3),'reader_backend':'current_python_streaming_reader',
            'reader_python_executable':sys.executable,'reader_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'zstandard_read_across_frames':True}


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--inventory-stdout':
        print(json.dumps(inventory(sys.argv[2],allow_system_fallback=False),separators=(',',':')))
        raise SystemExit(0)
    output=Path(sys.argv[1]);reports=[inventory(p) for p in sys.argv[2:]]
    result={'status':'INVENTORIED','files':reports,'read_only':True,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if len(reports)==2:
        a,b=reports
        result['native_type_byte_deltas']={name:b['native_types'].get(name,{}).get('payload_bytes',0)-a['native_types'].get(name,{}).get('payload_bytes',0) for name in sorted(set(a['native_types'])|set(b['native_types'])) if b['native_types'].get(name,{}).get('payload_bytes',0)!=a['native_types'].get(name,{}).get('payload_bytes',0)}
    output.write_text(json.dumps(result,indent=2)+'\n')
    for report in reports:
        print(report['path'], 'MDeformVert',report['native_types'].get('MDeformVert'),'MDeformWeight',report['native_types'].get('MDeformWeight'),flush=True)
