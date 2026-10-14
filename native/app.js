/** Render original captured teaching screens using native, guarded browser controls. */
import {DATA} from './content.js';
import {Lesson,frontier,shuffled,decodeState,encodeState,readRawDraft,rawDraftToken,scoreSummary,currency,NUMBERS,parseNumber,numericResult,allNodes} from './engine.js';

const $=id=>document.getElementById(id);
let lesson,orders=new Map(),saveSequence=0;
const create=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
const showMessage=text=>{const node=create('p',text,'notice warning');node.setAttribute('role','alert');$('lesson').prepend(node);};
async function save() {
  const sequence=++saveSequence,state=structuredClone(lesson.state),view=lesson.view,raw=structuredClone(lesson.rawNumbers);
  document.documentElement.dataset.saving='true';
  try {
    const token=await encodeState(state);
    if(sequence!==saveSequence)return;
    const url=new URL(location.href);url.searchParams.set('progress',token);url.searchParams.set('view',String(view));
    if(NUMBERS.some(g=>g.stage===state.s)&&Object.keys(raw).length)url.searchParams.set('draft',rawDraftToken(raw));else url.searchParams.delete('draft');
    history.replaceState(null,'',url);$('save-error').hidden=true;
  } catch(error) {
    if(sequence!==saveSequence)return;
    $('save-error').textContent='Your address could not be updated. Keep this tab open; copying or refreshing may not preserve the latest input.';
    $('save-error').hidden=false;console.error(error);
  } finally {if(sequence===saveSequence)document.documentElement.dataset.saving='false';}
}
async function prepareOrders() {
  const entries=DATA.groups.flatMap(g=>g.items.map(i=>[i.id,i.options,g.salt+i.id]));
  for(const g of NUMBERS)for(const c of g.choices)entries.push([`${g.prefix}:${c.key}`,c.options,c.salt]);
  orders=new Map(await Promise.all(entries.map(async([k,options,salt])=>[k,await shuffled(options,lesson.state[DATA.seedKey],salt)])));
}
function move(direction) {if(lesson.move(direction)){render();save();resetScroll();}}
function resetScroll(){window.scrollTo({top:0,left:0,behavior:'instant'});$('lesson').focus({preventScroll:true});}
function radio(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const g=NUMBERS.find(g=>g.stage===lesson.position.stage),c=g?.choices.find(c=>node.key===`widget_${g.prefix}_${c.key}`),group=DATA.groups.find(g=>g.stage===lesson.position.stage),item=group?.items[lesson.position.index];
  const selected=c?(lesson.state[DATA.draftKey][g.draft][c.key]??lesson.state[c.stateKey]):lesson.state[DATA.draftKey][group.draft][item.id];
  const options=orders.get(c?`${g.prefix}:${c.key}`:item.id),fieldset=create('fieldset');fieldset.append(create('legend',node.label));
  for(const [i,option] of options.entries()) {const label=create('label',undefined,'choice'),input=create('input');input.type='radio';input.name=node.key;input.value=option;input.id=`${node.key}_${i}`;input.checked=option===selected;
    input.addEventListener('change',()=>{if(c?lesson.draftNumericChoice(c.key,option):lesson.draftChoice(option))save();});label.append(input,create('span',option));fieldset.append(label);}
  return fieldset;
}
function number(node) {
  if(lesson.reviewing)return document.createDocumentFragment();const g=NUMBERS.find(g=>g.stage===lesson.position.stage),key=node.key.slice(`widget_${g.prefix}_`.length);
  const wrapper=create('div',undefined,'amount'),label=create('label',node.label),row=create('div',undefined,'amount-row'),input=create('input');
  label.htmlFor=node.key;input.id=node.key;input.type='text';input.inputMode=node.decimal?'decimal':'numeric';input.maxLength=64;input.value=lesson.rawNumbers[key]??String(lesson.state[DATA.draftKey][g.draft][key]??lesson.state[g.valuesKey][key]??0);
  input.addEventListener('input',()=>{if(lesson.draftNumber(key,input.value)){input.setAttribute('aria-invalid',String(parseNumber(input.value,g,key)===null));save();}});row.append(input);
  for(const [symbol,d] of [['−',-1],['+',1]]) {const b=create('button',symbol);b.type='button';b.setAttribute('aria-label',`${d<0?'Decrease':'Increase'} ${node.label} by ${node.step}`);b.addEventListener('click',()=>{const n=parseNumber(input.value,g,key);if(n===null)return;input.value=String(Math.max(node.min,Math.min(node.max,Number((n+d*node.step).toFixed(8)))));input.dispatchEvent(new Event('input',{bubbles:true}));});row.append(b);}
  wrapper.append(label,row);return wrapper;
}
function csv(rows,columns) {return columns.map(x=>`"${x.replaceAll('"','""')}"`).join(',')+'\r\n'+rows.map(row=>columns.map(key=>`"${String(row[key]).replaceAll('"','""')}"`).join(',')).join('\r\n')+'\r\n';}
function table(node,index) {
  const section=create('section'),wrap=create('div',undefined,'table-wrap'),element=create('table');
  if(node.fixedRows){element.className='aging-schedule';wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Aging schedule: age buckets across the top. Scroll horizontally to view each bucket; the total column stays visible.');}
  const caption=create('caption','Case evidence table');caption.className='visually-hidden';
  element.append(caption);const columns=Object.keys(node.rows[0]),head=create('thead'),tr=create('tr'),body=create('tbody');
  let rows=[...node.rows],sort=null,descending=false;
  const renderRows=()=>{body.replaceChildren();for(const row of rows){const line=create('tr');columns.forEach((key,i)=>{const cell=create(node.fixedRows&&i===0?'th':'td',String(row[key]));if(node.fixedRows&&i===0)cell.scope='row';line.append(cell);});body.append(line);}};
  columns.forEach(key=>{const cell=create('th');cell.scope='col';
    if(node.fixedRows){cell.textContent=key;tr.append(cell);return;}
    const button=create('button',key);button.type='button';
    button.addEventListener('click',()=>{descending=sort===key?!descending:false;sort=key;
      rows=[...node.rows].sort((a,b)=>String(a[key]).localeCompare(String(b[key]),'en')*(descending?-1:1));
      for(const header of tr.children)header.removeAttribute('aria-sort');cell.setAttribute('aria-sort',descending?'descending':'ascending');renderRows();});
    cell.append(button);tr.append(cell);});
  head.append(tr);element.append(head,body);renderRows();wrap.append(element);section.append(wrap);
  if(node.fixedRows){const hint=create('p','Age buckets run across the top. On a narrow screen, scroll the schedule horizontally to see every age bucket; totals remain visible on the right.','caption table-help');section.append(hint);}
  const tools=create('div',undefined,'table-tools'),download=create('button','Download table as CSV');download.type='button';
  const expand=create('button','Expand table');expand.type='button';
  expand.addEventListener('click',()=>{
    const dialog=create('dialog',undefined,'expanded-table'),title=create('h2',caption.textContent),close=create('button','Close table');
    const placeholder=document.createComment('Table location');wrap.before(placeholder);
    close.type='button';close.addEventListener('click',()=>dialog.close());
    dialog.append(title,close,wrap);document.body.append(dialog);
    dialog.addEventListener('close',()=>{placeholder.replaceWith(wrap);dialog.remove();expand.focus();},{once:true});
    dialog.showModal();
  });
  tools.append(expand);
  download.addEventListener('click',()=>{const blob=new Blob([csv(rows,columns)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=create('a');
    link.href=url;link.download=`${DATA.slug}-stage-${lesson.position.stage}-table-${index+1}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  tools.append(download);section.append(tools);return section;
}
function html(node){const template=document.createElement('template');template.innerHTML=node.text;return template.content;}
function feedback(node){
  const g=NUMBERS.find(g=>g.stage===lesson.position.stage),field=g.fields.find(([,label])=>label===node.label),choice=g.choices.find(c=>c.label===node.label),checked=numericResult(lesson.state,g);
  const correct=field?checked.fields[field[0]].correct:checked.choices[choice.key].correct;
  const templates=allNodes(DATA.screens[lesson.view].variants[correct?'correct':'wrong']).filter(x=>x.kind==='feedback');const template=templates.find(x=>x.label===node.label);
  let value;
  if(choice)value=lesson.state[choice.stateKey];else {const key=field[0],n=lesson.state[g.valuesKey][key];
    value='Submitted '+(g.prefix==='quantity'?n.toLocaleString('en-US'):g.prefix==='analysis'&&key==='inventory_turnover'?n.toFixed(2)+' times':g.prefix==='analysis'&&key==='days_in_inventory'?Math.trunc(n)+' days':currency(n));}
  const row=create('div',undefined,'feedback-row '+(correct?'correct':'review')),left=create('div');left.append(create('div',node.label+' - '+(correct?'Correct':'Review'),'feedback-label'),create('div',template.detail,'feedback-detail'));row.append(left,create('div',value,'feedback-value'));return row;
}
function tabs(node,index){
  const wrap=create('section'),list=create('div',undefined,'tab-list');list.setAttribute('role','tablist');list.setAttribute('aria-label','Cost-flow methods');const panels=[];
  node.children.forEach((child,i)=>{const tab=create('button',child.label),panel=create('div',undefined,'tab-panel'),id=`tab-${lesson.view}-${index}-${i}`;tab.type='button';tab.id=id;tab.setAttribute('role','tab');tab.setAttribute('aria-controls',id+'-panel');panel.id=id+'-panel';panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',id);child.children.forEach((n,j)=>panel.append(renderNode(n,j)));panels.push(panel);list.append(tab);});
  const activate=i=>{[...list.children].forEach((tab,j)=>{tab.setAttribute('aria-selected',String(j===i));tab.tabIndex=j===i?0:-1;panels[j].hidden=j!==i;});};
  [...list.children].forEach((tab,i)=>{tab.addEventListener('click',()=>activate(i));tab.addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight')next=(i+1)%panels.length;if(e.key==='ArrowLeft')next=(i+panels.length-1)%panels.length;if(e.key==='Home')next=0;if(e.key==='End')next=panels.length-1;if(next!==undefined){e.preventDefault();activate(next);list.children[next].focus();}});});activate(0);wrap.append(list,...panels);return wrap;
}
function renderNode(node,index) {
  if(node.kind==='html')return html(node);
  if(node.kind==='feedback')return feedback(node);
  if(node.kind==='tabs')return tabs(node,index);
  if(node.kind==='radio')return radio(node);
  if(node.kind==='number')return number(node);
  if(node.kind==='table')return table(node,index);
  if(node.kind==='button') {
    if(lesson.reviewing)return document.createDocumentFragment();
    const button=create('button',node.label,'primary');button.type='button';
    button.addEventListener('click',()=>{
      let result;
      if(node.label.startsWith('Check')) {
        result=lesson.numberGroup()?lesson.submitNumbers():lesson.submitChoice();
        if(!result){showMessage(lesson.numberGroup()?'Complete each choice and enter amounts in the stated units and ranges before checking.':'Choose a response before checking your reasoning.');return;}
      }else result=lesson.advance();
      if(result){render();save();if(!node.label.startsWith('Check'))resetScroll();}
    });return button;
  }
  if(node.kind==='progress') {
    const box=create('div',node.text,'case-progress'),bar=create('progress');bar.max=1;bar.value=node.value;bar.setAttribute('aria-label',node.text);box.append(bar);return box;
  }
  if(node.kind==='columns'||node.kind==='column') {
    const column=create('div',undefined,node.kind==='columns'?'columns':null);if(node.kind==='columns')column.style.setProperty('--columns',node.children.length);
    node.children.forEach((child,index)=>column.append(renderNode(child,index)));return column;
  }
  if(node.kind==='metric') {
    const metric=create('div',undefined,'metric');metric.append(create('span',node.label),create('strong',String(node.value)));
    if(node.delta!==undefined)metric.append(create('div',node.delta,'delta'+(String(node.delta).startsWith('-')?' negative':'')));return metric;
  }
  if(node.kind==='details') {
    const details=create('details'),summary=create('summary',node.label);details.append(summary);node.children.forEach((child,index)=>details.append(renderNode(child,index)));return details;
  }
  if(node.kind==='markdown') {
    const fragment=document.createDocumentFragment(),lines=node.text.split('\n').map(x=>x.trim()).filter(Boolean);
    if(lines.every(line=>/^\d+\./.test(line))) {const list=create('ol');for(const line of lines)list.append(create('li',line.replace(/^\d+\.\s*/,'')));fragment.append(list);}
    else for(const line of lines)fragment.append(create('p',line));return fragment;
  }
  let text=node.text;
  if(node.kind==='caption'&&lesson.position.stage===DATA.positions.at(-1).stage&&text.startsWith('First-pass evidence:')) {const score=scoreSummary(lesson.state);text=`First-pass evidence: ${score.correct} of ${score.attempted} attempted checkpoints correct; ${score.revisions} revision(s). Final mastery: complete`;}
  const heading=node.kind==='header'?'h2':node.kind==='subheader'?'h3':'p';
  const result=create(heading,text,['success','warning','info'].includes(node.kind)?`notice ${node.kind}`:node.kind==='caption'?'caption':null);
  if(['success','warning','info'].includes(node.kind))result.setAttribute('role','status');return result;
}
function render() {
  const position=lesson.position,screen=DATA.screens[lesson.view],group=DATA.groups.find(g=>g.stage===position.stage);
  let variant='unanswered';
  const numeric=NUMBERS.find(g=>g.stage===position.stage);
  if(numeric)variant=lesson.state[numeric.submittedKey]?(numericResult(lesson.state,numeric).correct?'correct':'wrong'):'unanswered';
  else if(group){const item=group.items[position.index],response=lesson.state[group.responseKey][item.id];variant=response===undefined?'unanswered':response===item.correct?'correct':'wrong';}
  $('hero').replaceChildren(...DATA.hero.map(html));
  $('page-counter').textContent=`Page ${lesson.view+1} of ${DATA.positions.length}`;
  $('back').disabled=lesson.view===0;$('forward').disabled=lesson.view>=frontier(lesson.state);$('reset').disabled=lesson.reviewing;
  $('stages').replaceChildren(...DATA.stages.map((label,stage)=>create('div',label,'stage-pill '+(stage<position.stage?'complete':stage===position.stage?'active':''))));
  $('review-message').replaceChildren();
  if(lesson.reviewing){const info=create('p','Review only. Return to your current page to continue the activity.','notice info');info.setAttribute('role','status');$('review-message').append(info);}
  const nodes=screen.variants[variant].map(renderNode);$('lesson').replaceChildren(...nodes);
  $('lesson').setAttribute('aria-busy','false');document.documentElement.dataset.view=String(lesson.view);
  document.documentElement.dataset.reached=String(frontier(lesson.state));
}
async function initialize() {
  if(!globalThis.CompressionStream||!globalThis.DecompressionStream||!globalThis.crypto?.subtle||!globalThis.structuredClone)throw new Error('Required native browser APIs are unavailable');
  const query=new URL(location.href).searchParams,token=query.get('progress'),state=token?await decodeState(token):null;
  lesson=new Lesson(state??undefined,query.get('view')??undefined,readRawDraft(query.get('draft')));
  await prepareOrders();render();if(token&&!state)showMessage('This saved link could not be restored. A new inventory case has been opened.');
  await save();document.documentElement.dataset.ready='true';performance.mark('lesson-ready');
}
$('back').addEventListener('click',()=>move(-1));$('forward').addEventListener('click',()=>move(1));
$('reset').addEventListener('click',async()=>{if(lesson.reset()){await prepareOrders();render();await save();resetScroll();}});
window.addEventListener('popstate',initialize);
initialize().catch(error=>{
  $('lesson').replaceChildren(create('p','This browser could not open the saved activity. Use a current browser with JavaScript, Web Crypto, BigInt, and Compression Streams enabled.','notice warning'));
  $('lesson').setAttribute('aria-busy','false');console.error(error);
});
