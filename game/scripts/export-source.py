"""Export reusable game source without private Sites/Git/runtime metadata."""
import pathlib,subprocess,sys,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
out=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root.parent/'Chosun_Campus_Walk_Source.zip'
files=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
excluded={'.openai','.git','node_modules','.sites-runtime','qa','__pycache__'}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in files:
  if not name:continue
  p=pathlib.Path(name)
  if any(part in excluded for part in p.parts) or p.name.startswith('.env'):continue
  if (root/p).is_file():z.write(root/p,'Chosun_Campus_Walk/'+name)
print(out)
