import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {assessKnownTyreContacts} from '../tests/helpers/known-tyre-limits.mjs';
const load=async path=>JSON.parse(await fs.readFile(new URL('../'+path,import.meta.url),'utf8'));
const hash=async path=>crypto.createHash('sha256').update(await fs.readFile(new URL('../'+path,import.meta.url))).digest('hex');
const changePath='tests/closeout-evidence/known-limit-adjustment/change.json',change=await load(changePath),before=await load(change.preservedBefore),after=await load(change.file),expected=structuredClone(before);
assert.equal(await hash(change.preservedBefore),change.beforeSha256);assert.equal(await hash(change.file),change.afterSha256);assert.equal(change.changes.length,2);
for(const c of change.changes){assert(['421_front_to_middle_forward','421_front_to_middle_reverse'].includes(c.route));assert.equal(c.field,'maximumRadialOverlapMeters');assert.equal(expected.routes[c.route][c.field],c.before);expected.routes[c.route][c.field]=c.after;}
assert.deepEqual(after,expected,'Only exact approved depth fields may change');
const reportPath='tests/runtime-runs/site-closeout.json',report=await load(reportPath),resultPath='tests/runtime-runs/site-closeout-results/site-closeout-results.json',source=await load(resultPath);assert.equal(await hash(resultPath),report.resultSnapshots[resultPath]);assert.equal(report.inputSha256[change.file],change.beforeSha256);
const oldFailures=source.results.filter(r=>!r.pass);assert.deepEqual(oldFailures.map(r=>r.id).sort(),change.changes.map(c=>c.route).sort());
const results=structuredClone(source.results);
for(const r of results){if(!r.hits)continue;const assessment=assessKnownTyreContacts(r.id,r.hits,after);r.knownContactAssessment=assessment;r.unresolvedHits=assessment.accepted?[]:r.hits;r.pass=r.complete&&r.verticalError<.25&&!r.unresolvedHits.length&&!r.wheelSupportFailures.length;}
assert(results.every(r=>r.pass),'New body, support, pose, count or unapproved contact remains a failure');
const inputSha256={};for(const p of [changePath,change.file,change.preservedBefore,reportPath,resultPath,'tests/helpers/known-tyre-limits.mjs','scripts/reassess-site-known-limits.mjs','dist/game.js','dist/wheel-suspension.js'])inputSha256[p]=await hash(p);
const result={passed:true,nativeSourceSha256:report.nativeSourceSha256,rawGLBSha256:report.rawGLBSha256,sourceRun:reportPath,sourceResults:resultPath,inputSha256,allowedInputRevision:change,strictOriginalPassed:source.passed,scope:'Read-only reassessment of the identical saved20 actual movement results; only two exact approved tyre-depth maxima changed. The original strict run and its failed status are preserved.',results};
await fs.writeFile(new URL('../tests/site-closeout-acceptance-results.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({passed:result.passed,actualRecords:results.length,oldFailures:oldFailures.map(r=>r.id),onlyApprovedDepthReassessment:true}));
