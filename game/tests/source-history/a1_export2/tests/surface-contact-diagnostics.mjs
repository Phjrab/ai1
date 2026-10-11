process.env.CAMPUS_SURFACE_POINTS=new URL('./fixtures/final-export2-surface-20.json',import.meta.url).pathname;
await import('./surface-conformity.mjs');
