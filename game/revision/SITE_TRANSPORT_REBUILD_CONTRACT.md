# Reconstructible Site transport contract

The canonical lighting source remains an unsplit schema-2 release. No Site deployment or credential creation is part of this checkpoint.

For a later authorized Site build, add dist/site-asset-loader.js and split only the exact campus.glb bytes into <=8 MiB .bin parts with a size/SHA256 manifest. Preserve the original release manifest at dist/data/site-original-release-manifest.json and retain all lightingRevision fields. Each part and the reassembled buffer must match its declared SHA before GLTFLoader.parseAsync. Keep other asset loadAsync calls unchanged. Do not recompress or quantize any asset.

The sole reversible game hooks are a leading import of loadSiteAsset from './site-asset-loader.js' and this exact loadWorld replacement:

Before:
```js
map(name=>loader.loadAsync(`./assets/${name}`,e=>{
```
After:
```js
map(name=>loadSiteAsset(loader,name,e=>{
```

This replaces the URL argument with the canonical asset name while retaining the progress callback. Reverse both hooks to verify canonical game.js exactly. Scope the adapter to campus.glb; all other names delegate to loader.loadAsync.


Site metadata must identify the canonical release manifest hash, source/augmented native hashes, part hashes/sizes, reconstructed campus hash, adapter hash and delivery verifier. Site transfer success is separate from browser/GPU execution. The prior adapter files were lost in the environment reset; this is a reconstruction contract, not a claim that an adapter currently runs.
