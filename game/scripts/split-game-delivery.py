#!/usr/bin/env python3
"""Wrap an already finalized game ZIP in bounded stored-ZIP parts and offline tools."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

MAX_PAYLOAD = 18 * 1024 * 1024
TOOLS = ('PARTS_MANIFEST.json', 'SHA256SUMS.txt', 'restore_game.py', 'restore_game.ps1', 'READ_ME_KO.txt')
RESTORE_COMMON = r'''import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

OUTPUT_NAME = 'Chosun_Campus_Walk_Lighting_Source.zip'
PREFIX = 'Chosun_Campus_Walk/'
REQUIRED = [PREFIX + name for name in (
    'dist/index.html', 'dist/game.js', 'dist/style.css', 'dist/street-lighting.js',
    'dist/street-lighting.json', 'dist/assets/lighting.glb', 'dist/assets/building.glb',
    'dist/assets/campus.glb', 'dist/release-manifest.json', 'tests/FINAL_VALIDATION.json',
    'SOURCE_MANIFEST.json', 'LIGHTING_SOURCE_MANIFEST.json')]

def need(condition, message):
    if not condition:
        raise ValueError(message)

def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()

def safe_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)

def validate_game_zip(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)), 'Game ZIP has duplicate paths')
        for name in names:
            relative = PurePosixPath(name)
            need(name.startswith(PREFIX) and '\\' not in name and not relative.is_absolute()
                 and '..' not in relative.parts and relative.as_posix() == name,
                 'Unsafe game ZIP path: ' + name)
        need(set(REQUIRED) <= set(names), 'Required game/runtime files are missing')
        need(archive.testzip() is None, 'Game ZIP internal CRC verification failed')
        index_bytes = archive.read(PREFIX + 'tests/FINAL_VALIDATION.json')
        index = json.loads(index_bytes)
        release = json.loads(archive.read(PREFIX + 'dist/release-manifest.json'))
        need(index.get('status') == 'bounded_lighting_passed_with_preserved_a65_limits',
             'This is not a finalized lighting game ZIP; checkpoints cannot be split')
        need(index.get('original362ChecksRerun') is False and index.get('fullSceneRerun') is False,
             'Unexpected validation scope')
        need(release.get('schema') == 2 and release.get('validationIndexSha256') == hashlib.sha256(index_bytes).hexdigest(),
             'Final release validation binding differs')
        lighting = index.get('lightingRevision', {})
        need(lighting == release.get('lightingRevision') and safe_hash(lighting.get('augmentedNativeSha256'))
             and safe_hash(lighting.get('nativeBindingSha256')), 'Final augmented-native binding is missing')
        binding_name = lighting.get('nativeBinding')
        need(isinstance(binding_name, str) and binding_name.startswith('revision/')
             and PREFIX + binding_name in names, 'Final native binding file is missing')
        binding_bytes = archive.read(PREFIX + binding_name)
        need(hashlib.sha256(binding_bytes).hexdigest() == lighting['nativeBindingSha256'], 'Native binding hash differs')
        binding = json.loads(binding_bytes)
        need(binding.get('status') == 'final_augmented_native_bound'
             and binding.get('augmentedNativeSha256') == lighting['augmentedNativeSha256'], 'Native binding is not final')
        source = json.loads(archive.read(PREFIX + 'LIGHTING_SOURCE_MANIFEST.json'))
        records = source.get('files', {})
        need(set(names) == {PREFIX + name for name in records} | {PREFIX + 'LIGHTING_SOURCE_MANIFEST.json'},
             'Game ZIP source-manifest file set differs')
        for name, record in records.items():
            info = archive.getinfo(PREFIX + name)
            hasher = hashlib.sha256()
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    hasher.update(block)
            need(info.file_size == record['bytes'] and hasher.hexdigest() == record['sha256'],
                 'Game ZIP source hash/size differs: ' + name)
    return True

def read_manifest(root):
    path = root / 'PARTS_MANIFEST.json'
    need(path.is_file() and not path.is_symlink(), 'PARTS_MANIFEST.json is missing or a symlink')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    need(manifest.get('format') == 1 and manifest.get('kind') == 'chosun_final_game_zip_parts', 'Wrong parts manifest')
    source = manifest['sourceZip']
    need(source['name'] == OUTPUT_NAME and safe_hash(source['sha256']) and type(source['bytes']) is int
         and source['bytes'] > 0, 'Invalid source ZIP identity')
    maximum = manifest['partPayloadMaximumBytes']
    need(type(maximum) is int and 0 < maximum <= 18 * 1024 * 1024, 'Invalid part size limit')
    parts = manifest['parts']
    need(isinstance(parts, list) and 0 < len(parts) <= 9999, 'Invalid part count')
    total = 0
    for number, part in enumerate(parts, 1):
        need(part['index'] == number and part['name'] == 'Chosun_Game_Part_%04d.zip' % number
             and part['payloadName'] == 'payload.bin' and part['offset'] == total, 'Invalid part name/order/offset')
        need(type(part['payloadBytes']) is int and 0 < part['payloadBytes'] <= maximum
             and safe_hash(part['payloadSha256']) and safe_hash(part['zipSha256'])
             and type(part['zipBytes']) is int and part['zipBytes'] > part['payloadBytes'], 'Invalid part size/hash')
        if number < len(parts):
            need(part['payloadBytes'] == maximum, 'Non-final part is not the declared chunk size')
        total += part['payloadBytes']
    need(total == source['bytes'], 'Part byte total differs from the original ZIP')
    return manifest
'''

RESTORE_PY = RESTORE_COMMON + r'''
def restore(root):
    manifest = read_manifest(root)
    output = root / OUTPUT_NAME
    need(not output.exists() and not output.is_symlink(), 'Output already exists; refusing to overwrite: ' + OUTPUT_NAME)
    source = manifest['sourceZip']
    temporary_file = tempfile.NamedTemporaryFile(prefix='.game-restore-', suffix='.zip', dir=root, delete=False)
    temporary = Path(temporary_file.name)
    temporary_file.close()
    combined = hashlib.sha256()
    total = 0
    try:
        with temporary.open('wb') as destination:
            for part in manifest['parts']:
                path = root / part['name']
                need(path.is_file() and not path.is_symlink(), 'Missing part: ' + part['name'])
                need(path.stat().st_size == part['zipBytes'] and digest(path) == part['zipSha256'],
                     'Part ZIP hash/size differs: ' + part['name'])
                with zipfile.ZipFile(path) as archive:
                    need(archive.namelist() == ['payload.bin'], 'Part contains unexpected files: ' + part['name'])
                    info = archive.getinfo('payload.bin')
                    need(info.compress_type == zipfile.ZIP_STORED and info.file_size == part['payloadBytes']
                         and info.compress_size == info.file_size, 'Part payload is not the declared stored data')
                    payload_hash = hashlib.sha256()
                    size = 0
                    with archive.open(info) as payload:
                        for block in iter(lambda: payload.read(1024 * 1024), b''):
                            destination.write(block)
                            payload_hash.update(block)
                            combined.update(block)
                            size += len(block)
                    need(size == part['payloadBytes'] and payload_hash.hexdigest() == part['payloadSha256'],
                         'Payload hash/size differs: ' + part['name'])
                    need(archive.testzip() is None, 'Part CRC failed: ' + part['name'])
                    total += size
        need(total == source['bytes'] and combined.hexdigest() == source['sha256']
             and digest(temporary) == source['sha256'], 'Reconstructed ZIP differs from the original')
        validate_game_zip(temporary)
        # Exclusive creation works on Windows and Unix, including filesystems without hard links.
        created = False
        try:
            with output.open('xb') as destination, temporary.open('rb') as stream:
                created = True
                shutil.copyfileobj(stream, destination, 1024 * 1024)
            need(output.stat().st_size == source['bytes'] and digest(output) == source['sha256'], 'Final output copy differs')
        except BaseException:
            if created:
                output.unlink(missing_ok=True)
            raise
    finally:
        temporary.unlink(missing_ok=True)
    print('Restored and verified: ' + OUTPUT_NAME)
    print('SHA256: ' + source['sha256'])
    print('ZIP CRC, required runtime files and final native binding verified.')

if __name__ == '__main__':
    try:
        restore(Path(__file__).resolve().parent)
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit('Restore failed; original parts were not changed: ' + str(error))
'''

RESTORE_PS = r'''$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Root = $PSScriptRoot
$OutputName = 'Chosun_Campus_Walk_Lighting_Source.zip'
function Need($Condition, [string]$Message) { if (-not $Condition) { throw $Message } }
function Hex($Bytes) { return [BitConverter]::ToString($Bytes).Replace('-', '').ToLowerInvariant() }
function HashFile([string]$Path) {
    $stream = [IO.File]::OpenRead($Path); $hash = [Security.Cryptography.SHA256]::Create()
    try { return Hex ($hash.ComputeHash($stream)) } finally { $hash.Dispose(); $stream.Dispose() }
}
function PlainFile([string]$Path) {
    Need ([IO.File]::Exists($Path)) ('Missing file: ' + $Path)
    Need ((([IO.File]::GetAttributes($Path)) -band [IO.FileAttributes]::ReparsePoint) -eq 0) ('Symlink/reparse point refused: ' + $Path)
}
function JsonEntry($Archive, [string]$Name) {
    $entry = $Archive.GetEntry($Name); Need ($null -ne $entry) ('Missing game file: ' + $Name)
    $reader = [IO.StreamReader]::new($entry.Open(), [Text.Encoding]::UTF8)
    try { return ($reader.ReadToEnd() | ConvertFrom-Json) } finally { $reader.Dispose() }
}
# CRC32 of every decompressed entry is checked against its central-directory CRC.
# This uses only built-in .NET and handles the bounded, non-ZIP64 delivery archive.
if (-not ('GameZipCrc' -as [type])) { Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
public static class GameZipCrc {
    static readonly uint[] Table = MakeTable();
    static uint[] MakeTable() { uint[] t = new uint[256]; for (uint i=0;i<256;i++) { uint c=i; for(int k=0;k<8;k++) c=(c&1)!=0?0xedb88320U^(c>>1):c>>1; t[i]=c; } return t; }
    public static uint Compute(Stream stream) { uint crc=0xffffffffU; byte[] b=new byte[1048576]; int n; while((n=stream.Read(b,0,b.Length))>0) for(int i=0;i<n;i++) crc=Table[(crc^b[i])&255]^(crc>>8); return crc^0xffffffffU; }
    public static Dictionary<string,uint> Expected(string path) {
        var result=new Dictionary<string,uint>(StringComparer.Ordinal);
        using(var stream=File.OpenRead(path)) using(var r=new BinaryReader(stream)) {
            int len=(int)Math.Min(stream.Length,65557); stream.Position=stream.Length-len; byte[] tail=r.ReadBytes(len); int end=-1;
            for(int i=len-22;i>=0;i--) if(BitConverter.ToUInt32(tail,i)==0x06054b50 && i+22+BitConverter.ToUInt16(tail,i+20)==len) { end=i; break; }
            if(end<0) throw new InvalidDataException("Missing ZIP end record");
            ushort count=BitConverter.ToUInt16(tail,end+10); uint offset=BitConverter.ToUInt32(tail,end+16);
            if(BitConverter.ToUInt16(tail,end+4)!=0 || BitConverter.ToUInt16(tail,end+6)!=0 || count==65535 || offset==0xffffffffU) throw new InvalidDataException("Multidisk/ZIP64 archives are outside this delivery format");
            stream.Position=offset;
            for(int i=0;i<count;i++) {
                byte[] h=r.ReadBytes(46); if(h.Length!=46 || BitConverter.ToUInt32(h,0)!=0x02014b50) throw new InvalidDataException("Invalid ZIP directory");
                ushort flags=BitConverter.ToUInt16(h,8), n=BitConverter.ToUInt16(h,28), extra=BitConverter.ToUInt16(h,30), comment=BitConverter.ToUInt16(h,32);
                byte[] name=r.ReadBytes(n); if(name.Length!=n) throw new InvalidDataException("Truncated ZIP name");
                if((flags&0x800)==0) foreach(byte b in name) if(b>127) throw new InvalidDataException("Non-UTF8 archive names are outside this delivery format");
                string key=Encoding.UTF8.GetString(name); if(result.ContainsKey(key)) throw new InvalidDataException("Duplicate ZIP path");
                result.Add(key,BitConverter.ToUInt32(h,16)); stream.Seek(extra+comment,SeekOrigin.Current);
            }
        } return result;
    }
}
'@
}
$ManifestPath = Join-Path $Root 'PARTS_MANIFEST.json'; PlainFile $ManifestPath
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
Need ($Manifest.format -eq 1 -and $Manifest.kind -eq 'chosun_final_game_zip_parts') 'Wrong parts manifest'
Need ($Manifest.sourceZip.name -ceq $OutputName -and $Manifest.sourceZip.sha256 -cmatch '^[a-f0-9]{64}$' -and [long]$Manifest.sourceZip.bytes -gt 0) 'Invalid source identity'
$Parts = @($Manifest.parts); $Max = [long]$Manifest.partPayloadMaximumBytes
Need ($Parts.Count -gt 0 -and $Parts.Count -le 9999 -and $Max -gt 0 -and $Max -le 18874368) 'Invalid part size/count'
$Total = [long]0
for ($i=0; $i -lt $Parts.Count; $i++) {
    $p=$Parts[$i]; $ExpectedName='Chosun_Game_Part_{0:D4}.zip' -f ($i+1)
    Need ($p.index -eq $i+1 -and $p.name -ceq $ExpectedName -and $p.payloadName -ceq 'payload.bin' -and [long]$p.offset -eq $Total) 'Invalid part path/order'
    Need ([long]$p.payloadBytes -gt 0 -and [long]$p.payloadBytes -le $Max -and [long]$p.zipBytes -gt [long]$p.payloadBytes -and $p.payloadSha256 -cmatch '^[a-f0-9]{64}$' -and $p.zipSha256 -cmatch '^[a-f0-9]{64}$') 'Invalid part hash/size'
    if ($i -lt $Parts.Count-1) { Need ([long]$p.payloadBytes -eq $Max) 'Non-final part is not full' }
    $Total += [long]$p.payloadBytes
}
Need ($Total -eq [long]$Manifest.sourceZip.bytes) 'Part byte totals differ'
$Output = Join-Path $Root $OutputName
Need (-not (Test-Path -LiteralPath $Output)) 'Output exists; refusing to overwrite'
$Temporary = Join-Path $Root ('.game-restore-' + [Guid]::NewGuid().ToString('N') + '.zip')
try {
    $dest = [IO.File]::Open($Temporary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
    try {
        $buffer = New-Object byte[] 1048576
        foreach ($p in $Parts) {
            $partPath=Join-Path $Root $p.name; PlainFile $partPath
            Need ((Get-Item -LiteralPath $partPath).Length -eq [long]$p.zipBytes -and (HashFile $partPath) -ceq $p.zipSha256) ('Part ZIP hash/size differs: '+$p.name)
            $partFile=[IO.File]::OpenRead($partPath); $archive=[IO.Compression.ZipArchive]::new($partFile,[IO.Compression.ZipArchiveMode]::Read)
            try {
                Need ($archive.Entries.Count -eq 1 -and $archive.Entries[0].FullName -ceq 'payload.bin') 'Unexpected part entries'
                $entry=$archive.Entries[0]; Need ($entry.Length -eq [long]$p.payloadBytes -and $entry.CompressedLength -eq $entry.Length) 'Part is not the declared stored payload'
                $payload=$entry.Open(); $hash=[Security.Cryptography.SHA256]::Create(); $size=[long]0
                try { while (($n=$payload.Read($buffer,0,$buffer.Length)) -gt 0) { $dest.Write($buffer,0,$n); [void]$hash.TransformBlock($buffer,0,$n,$buffer,0); $size+=$n }; [void]$hash.TransformFinalBlock([byte[]]@(),0,0)
                    Need ($size -eq [long]$p.payloadBytes -and (Hex $hash.Hash) -ceq $p.payloadSha256) 'Part payload hash/size differs'
                } finally { $hash.Dispose(); $payload.Dispose() }
            } finally { $archive.Dispose(); $partFile.Dispose() }
        }
    } finally { $dest.Dispose() }
    Need ((Get-Item -LiteralPath $Temporary).Length -eq [long]$Manifest.sourceZip.bytes -and (HashFile $Temporary) -ceq $Manifest.sourceZip.sha256) 'Restored ZIP differs from original'
    $expectedCrc=[GameZipCrc]::Expected($Temporary)
    $file=[IO.File]::OpenRead($Temporary); $game=[IO.Compression.ZipArchive]::new($file,[IO.Compression.ZipArchiveMode]::Read)
    try {
        $required=@('dist/index.html','dist/game.js','dist/style.css','dist/street-lighting.js','dist/street-lighting.json','dist/assets/lighting.glb','dist/assets/building.glb','dist/assets/campus.glb','dist/release-manifest.json','tests/FINAL_VALIDATION.json','SOURCE_MANIFEST.json','LIGHTING_SOURCE_MANIFEST.json')
        foreach ($name in $required) { Need ($null -ne $game.GetEntry('Chosun_Campus_Walk/'+$name)) ('Missing required runtime file: '+$name) }
        Need ($expectedCrc.Count -eq $game.Entries.Count) 'Game entry count differs'
        foreach ($entry in $game.Entries) {
            Need ($entry.FullName.StartsWith('Chosun_Campus_Walk/') -and $entry.FullName -notmatch '(^|/)\.\.(/|$)|\\') 'Unsafe game path'
            Need ($expectedCrc.ContainsKey($entry.FullName)) 'Entry missing from ZIP directory'
            $stream=$entry.Open(); try { Need (([GameZipCrc]::Compute($stream)) -eq $expectedCrc[$entry.FullName]) ('ZIP CRC failed: '+$entry.FullName) } finally { $stream.Dispose() }
        }
        $index=JsonEntry $game 'Chosun_Campus_Walk/tests/FINAL_VALIDATION.json'; $release=JsonEntry $game 'Chosun_Campus_Walk/dist/release-manifest.json'
        Need ($index.status -eq 'bounded_lighting_passed_with_preserved_a65_limits' -and $release.schema -eq 2) 'Game ZIP is not finalized'
        Need ($index.lightingRevision.augmentedNativeSha256 -ceq $release.lightingRevision.augmentedNativeSha256 -and $index.lightingRevision.augmentedNativeSha256 -cmatch '^[a-f0-9]{64}$') 'Final native identity differs'
    } finally { $game.Dispose(); $file.Dispose() }
    [IO.File]::Move($Temporary,$Output)
    Write-Host ('Restored and verified: '+$OutputName)
    Write-Host ('SHA256: '+$Manifest.sourceZip.sha256)
    Write-Host 'ZIP CRC and required runtime files verified.'
} finally { if ([IO.File]::Exists($Temporary)) { [IO.File]::Delete($Temporary) } }
'''

README_KO = '''도구 ZIP을 먼저 압축 해제하고, 두 개·세 개 또는 제공된 모든 파트 ZIP을 압축 해제한 도구 파일 옆에 놓으세요.

PARTS_MANIFEST.json에 적힌 파트가 하나라도 빠지면 복원이 중단됩니다.
파트 ZIP은 압축 해제하거나 이름을 바꾸지 마세요. 모든 파일을 로컬 폴더에 둡니다.

Python 3이 있는 경우: 그 폴더에서 python restore_game.py 를 실행합니다.
Windows PowerShell의 경우: 그 폴더에서 .\\restore_game.ps1 을 실행합니다.
PowerShell 보안 정책이 실행을 차단하면 정책을 바꾸지 말고 Python 방법을 이용하세요.
추가 패키지 설치나 네트워크 접속은 필요 없습니다.

복원 결과: Chosun_Campus_Walk_Lighting_Source.zip
원본 ZIP 바이트와 SHA256을 그대로 복구하며 내부 CRC와 필수 게임 파일을 검사합니다.
기존 출력 파일은 덮어쓰지 않습니다. 파트 손상/누락 시 오류를 확인하고 해당 파트를 다시 받으세요.
ZIP 복원은 게임 실행이나 브라우저/GPU 성능 검증이 아닙니다.
SHA256SUMS.txt는 파트·도구 파일과 복원할 원본 ZIP의 해시를 제공합니다.
'''


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def stored_zip(path, contents):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name, content in contents.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != list(contents) or archive.testzip() is not None:
            raise ValueError('Stored wrapper verification failed: ' + path.name)
        for name, content in contents.items():
            if archive.getinfo(name).compress_type != zipfile.ZIP_STORED or archive.read(name) != content:
                raise ValueError('Stored wrapper bytes differ: ' + path.name)


def split(source, output, part_bytes):
    if not source.is_file() or source.is_symlink():
        raise ValueError('Source must be an existing regular final game ZIP')
    if not 0 < part_bytes <= MAX_PAYLOAD:
        raise ValueError('Payload size must be between 1 byte and 18 MiB')
    if output.exists() or output.is_symlink():
        raise ValueError('Delivery directory exists; refusing to overwrite')
    size = source.stat().st_size
    if not 0 < size < 2**32 or (size + part_bytes - 1) // part_bytes > 9999:
        raise ValueError('Source exceeds the bounded non-ZIP64 delivery format')
    source_sha = sha(source)
    helpers = {'__name__': 'game_delivery_helpers'}
    exec(compile(RESTORE_COMMON, '<fixed restore helpers>', 'exec'), helpers)
    helpers['validate_game_zip'](source)
    with zipfile.ZipFile(source) as archive:
        if len(archive.infolist()) >= 65535 or any(info.file_size >= 2**32 for info in archive.infolist()):
            raise ValueError('ZIP64 source is outside this delivery format')
    if source.stat().st_size != size or sha(source) != source_sha:
        raise ValueError('Source changed during final-game validation')
    output.mkdir(parents=False, exist_ok=False)
    parts = []
    combined = hashlib.sha256()
    total = 0
    with source.open('rb') as stream:
        while payload := stream.read(part_bytes):
            number = len(parts) + 1
            name = 'Chosun_Game_Part_%04d.zip' % number
            path = output / name
            stored_zip(path, {'payload.bin': payload})
            parts.append({'index': number, 'name': name, 'payloadName': 'payload.bin', 'offset': total,
                          'payloadBytes': len(payload), 'payloadSha256': hashlib.sha256(payload).hexdigest(),
                          'zipBytes': path.stat().st_size, 'zipSha256': sha(path)})
            combined.update(payload)
            total += len(payload)
    if total != size or combined.hexdigest() != source_sha or sha(source) != source_sha:
        raise ValueError('Source changed during split; incomplete delivery must not be used')
    manifest = {'format': 1, 'kind': 'chosun_final_game_zip_parts', 'partPayloadMaximumBytes': part_bytes,
                'sourceZip': {'name': helpers['OUTPUT_NAME'], 'originalName': source.name,
                              'bytes': size, 'sha256': source_sha}, 'parts': parts}
    contents = {'PARTS_MANIFEST.json': (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
                'restore_game.py': RESTORE_PY.encode('utf-8'),
                'restore_game.ps1': b'\xef\xbb\xbf' + RESTORE_PS.encode('utf-8'),
                'READ_ME_KO.txt': README_KO.encode('utf-8')}
    sums = [(source_sha, helpers['OUTPUT_NAME'])] + [(p['zipSha256'], p['name']) for p in parts]
    sums += [(hashlib.sha256(data).hexdigest(), name) for name, data in contents.items()]
    contents['SHA256SUMS.txt'] = ''.join(digest + '  ' + name + '\n' for digest, name in sums).encode('utf-8')
    for name, content in contents.items():
        with (output / name).open('xb') as stream:
            stream.write(content)
    helpers['read_manifest'](output)
    tools_path = output / 'Chosun_Game_Restore_Tools.zip'
    stored_zip(tools_path, {name: contents[name] for name in TOOLS})
    return {'deliveryDirectory': str(output), 'sourceZip': manifest['sourceZip'], 'parts': len(parts),
            'payloadBytes': total, 'maximumPayloadBytes': part_bytes, 'sourceUnchanged': True,
            'storedWrappersCrcVerified': True, 'toolsZip': {'name': tools_path.name,
                'bytes': tools_path.stat().st_size, 'sha256': sha(tools_path)},
            'manifestSha256': sha(output / 'PARTS_MANIFEST.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_zip', type=Path)
    parser.add_argument('delivery_directory', type=Path)
    parser.add_argument('--part-bytes', type=int, default=MAX_PAYLOAD,
                        help='Payload bytes, at most 18 MiB; smaller values support synthetic tests')
    args = parser.parse_args()
    print(json.dumps(split(args.source_zip.absolute(), args.delivery_directory.absolute(), args.part_bytes), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise SystemExit('Game delivery split blocked: ' + str(error))
