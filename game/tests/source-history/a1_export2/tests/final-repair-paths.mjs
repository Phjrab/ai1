// Exercise every path touched by the last bounded repairs. The short shared
// branch probe comes directly from the native-bound, sampled endpoint contract.
// It is a test itinerary only; no floor/collision geometry is introduced.
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {WORLD} from '../dist/world-config.js';
const contract=JSON.parse(await fs.readFile(new URL('../data/final-pedestrian-navigation.json',import.meta.url),'utf8'));
const shared=contract.walking_shared_endpoint_adjustments;
assert.equal(shared?.length,1,'Final shared endpoint contract must be present');
const row=shared[0];assert.equal(row.index,1036);assert.equal(row.source_way_id,'1485907463');
const id='final_shared_endpoint_1485907463';
assert(!WORLD.pedestrianPaths.some(p=>p.id===id));
WORLD.pedestrianPaths.push({id,points:row.sampled_connector_points.map(p=>[p[0],p[2],-p[1]]),width:1.6,source_way_id:row.source_way_id});
const paths=['inferred_walk_connector_944569946_0','central108','inferred_walk_connector_1125125519_2','final_mapped_footway_947734765',id,'IT138_upper_approach_474301323','IT138_bridge_11134046237','IT138_bridge_4682911885','rv2_it_lounge_roof_to_lounge_route','rv2_it_lounge_mapped_entrance_route','rv2_it_lounge_level5_entrance_route'];
process.env.WALK_PATH_IDS=paths.join(',');process.env.WALK_SKIP_SURFACES='1';
await import('./walkable-paths.mjs');
