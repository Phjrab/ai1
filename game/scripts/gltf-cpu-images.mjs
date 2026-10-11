// Geometry/physics tasks in Node do not have a browser image decoder. Read PNG
// dimensions for Three's texture object while keeping all GPU/pixel rendering
// outside this check's claims. Production browser code does not import this.
export function installCPUImageMetadata(){
 globalThis.self??=globalThis;
 if(typeof globalThis.createImageBitmap==='function')return;
 globalThis.createImageBitmap=async blob=>{
  const bytes=new Uint8Array(await blob.arrayBuffer());
  if(bytes.length<24||[137,80,78,71,13,10,26,10].some((v,i)=>bytes[i]!==v))throw new Error('CPU geometry loader expects an embedded PNG; pixels were not decoded');
  const data=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),width=data.getUint32(16),height=data.getUint32(20);
  if(!width||!height)throw new Error('Invalid PNG dimensions');
  return {width,height,close(){},cpuMetadataOnly:true};
 };
}
