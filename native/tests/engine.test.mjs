import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DATA} from '../content.js';
import * as e from '../engine.js';
const fixtures=JSON.parse(readFileSync(new URL('./python-oracles.json',import.meta.url)));

test('Inventory calculations and every method match independent Python outcomes',()=>{
  assert.deepEqual(e.quantityReconciliation(),fixtures.calculations.quantity);
  assert.deepEqual(e.goodsAvailable(),fixtures.calculations.available);
  assert.deepEqual(e.methodResults(),fixtures.calculations.methods);
  for(const [method,values] of Object.entries(fixtures.calculations.metrics))for(const [key,value] of Object.entries(values))assert.ok(Math.abs(e.inventoryMetrics(method)[key]-value)<1e-12);
  for(const g of DATA.numbers)assert.deepEqual(e.expectedNumbers(g.prefix),fixtures.calculations.expected[g.prefix]);
  for(const [n,expected] of [[.5,0],[1.5,2],[2.5,2],[-.5,0],[-1.5,-2],[-2.5,-2]])assert.equal(e.pyRound(n)||0,expected);
});
test('Every Python option order matches exactly including 63-bit seeds',async()=>{for(const f of fixtures.shuffles)assert.deepEqual(await e.shuffled(f.input,BigInt(f.seed),f.salt),f.output);});
test('All original stage snapshots decode and native links round-trip losslessly',async()=>{
  for(const f of fixtures.snapshots){const restored=await e.decodeState(f.token);assert.ok(restored);const expected={...f.payload,[DATA.seedKey]:BigInt(f.seed??f.payload[DATA.seedKey])};assert.deepEqual(restored,expected);assert.deepEqual(await e.decodeState(await e.encodeState(restored)),restored);}
  for(const seed of [0n,9007199254740993n,9223372036854775807n]){const s=e.newState(seed);assert.equal((await e.decodeState(await e.encodeState(s)))[DATA.seedKey],seed);}
});
test('Invalid snapshots, future work, unknown and nonnumeric drafts are rejected',async()=>{
  const s=e.newState(0n);s.s=6;assert.throws(()=>e.validateSnapshot(s));
  for(const patch of [{extra:1},{qs:1},{qv:{ending_units:40}},{dr:{c:{},q:{student:'Alex'},k:{},r:{},a:{}}},{o:2**53}])assert.throws(()=>e.validateSnapshot({...e.newState(0n),...patch}));
  for(const token of ['', 'garbage', 'a'.repeat(16001)])assert.equal(await e.decodeState(token),null);
});
test('Complete validated route preserves wrong answers, repeat attempts and numeric recheck rules',()=>{
  const lesson=new e.Lesson(e.newState(42n));assert.ok(lesson.advance());
  while(lesson.state.s!==DATA.positions.at(-1).stage){
    const g=lesson.numberGroup();
    if(g){for(const c of g.choices)lesson.draftNumericChoice(c.key,c.options.find(x=>x!==c.correct));for(const [k] of g.fields)lesson.draftNumber(k,'0');assert.ok(lesson.submitNumbers());assert.equal(lesson.advance(),false);const attempts=structuredClone(lesson.state.at);assert.ok(lesson.submitNumbers());assert.deepEqual(lesson.state.at,attempts);for(const [k,v] of Object.entries(e.expectedNumbers(g.prefix)))lesson.draftNumber(k,String(v));for(const c of g.choices)lesson.draftNumericChoice(c.key,c.correct);assert.ok(lesson.submitNumbers());assert.equal(lesson.submitNumbers(),false);}
    else{const {group,item}=lesson.context();lesson.draftChoice(item.options.find(x=>x!==item.correct));assert.ok(lesson.submitChoice());assert.equal(lesson.advance(),false);assert.ok(lesson.submitChoice());assert.equal(lesson.state.at[`${group.prefix}:${item.id}`],2);lesson.draftChoice(item.correct);assert.ok(lesson.submitChoice());assert.equal(lesson.submitChoice(),false);}
    assert.ok(lesson.advance());
  }
  assert.equal(e.scoreSummary(lesson.state).attempted,e.scoreKeys().size);assert.equal(lesson.advance(),false);
  const complete=e.canonicalJSON(lesson.state);while(lesson.move(-1)){assert.equal(lesson.submitChoice(),false);assert.equal(lesson.submitNumbers(),false);assert.equal(lesson.draftChoice('anything'),false);assert.equal(lesson.draftNumber('ending_units','0'),false);assert.equal(lesson.draftNumericChoice('effect','anything'),false);assert.equal(lesson.reset(),false);assert.equal(lesson.advance(),false);assert.equal(e.canonicalJSON(lesson.state),complete);}while(lesson.move(1))assert.equal(e.canonicalJSON(lesson.state),complete);assert.equal(lesson.view,e.frontier(lesson.state));
});
test('View clamping, numeric units/ranges, draft text and first-pass scores remain bounded',()=>{
  const lesson=new e.Lesson(e.newState(0n),999);assert.equal(lesson.view,0);
  const [q,c,a]=DATA.numbers;assert.equal(e.parseNumber('40',q,'ending_units'),40);assert.equal(e.parseNumber('40.1',q,'ending_units'),null);assert.equal(e.parseNumber('501',q,'ending_units'),null);assert.equal(e.parseNumber('$10,400',c,'fifo_ending_inventory'),10400);assert.equal(e.parseNumber('10,40',c,'fifo_ending_inventory'),null);assert.equal(e.parseNumber('3.06',a,'inventory_turnover'),3.06);
  lesson.advance();const item=lesson.context().item;lesson.draftChoice(item.options.find(x=>x!==item.correct));for(let i=0;i<101;i++)lesson.submitChoice();assert.equal(lesson.state.v,DATA.extensionVersion);assert.equal(e.scoreSummary(lesson.state).revisions,100);
});
test('Final titles and all generated lesson variants contain no provisional branding',()=>{
  assert.match(readFileSync(new URL('../index.html',import.meta.url),'utf8'),/<title>Stockroom to Statements<\/title>/);
  const prose=JSON.stringify({hero:DATA.hero,screens:DATA.screens,groups:DATA.groups,numbers:DATA.numbers});assert.doesNotMatch(prose,/\b(?:pilot|preview|prototype|experimental)\b/i);
  assert.equal(DATA.screens.length,17);assert.ok(DATA.screens.every(x=>Object.keys(x.variants).length===3));
});
