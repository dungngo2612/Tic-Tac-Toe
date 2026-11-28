'use strict';
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const GLYPHS = {K:'帥',A:'仕',E:'相',H:'傌',R:'俥',C:'炮',P:'兵',k:'將',a:'士',e:'象',h:'馬',r:'車',c:'砲',p:'卒'};
const NAMES = {K:'Tướng',A:'Sĩ',E:'Tượng',H:'Mã',R:'Xe',C:'Pháo',P:'Tốt'};
let state, selected = null, busy = false, flipped = false, errorTimer;
function team(p) { return p ? (p === p.toUpperCase() ? 1 : -1) : 0; }
function svg(tag, attrs = {}, text = '') {
  const el = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key,value]) => el.setAttribute(key,value));
  if (text) el.textContent = text;
  return el;
}
function point(square) {
  let r = Math.floor(square/9), c = square%9;
  if (flipped) { r = 9-r; c = 8-c; }
  return [54+c*54,57+r*54];
}
function coord(square) { return String.fromCharCode(97+square%9)+(10-Math.floor(square/9)); }
function notify(message) {
  $('error').textContent = message; $('error').hidden = false;
  clearTimeout(errorTimer); errorTimer = setTimeout(() => $('error').hidden = true, 5500);
}
async function request(path, payload) {
  const options = payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)};
  const response = await fetch('./api/'+path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Không thể xử lý yêu cầu.');
  return data;
}
function finished() { return state && (state.winner !== null || state.draw); }
function aiTurn() { return state && state.mode === 'ai' && state.turn !== state.human && !finished(); }
function drawBoard() {
  const board = $('board'); board.replaceChildren();
  const defs = svg('defs');
  const gradient = svg('radialGradient',{id:'disc',cx:'35%',cy:'25%',r:'80%'});
  gradient.append(svg('stop',{offset:'0%','stop-color':'#fff0cc'}),svg('stop',{offset:'80%','stop-color':'#f0d49f'}),svg('stop',{offset:'100%','stop-color':'#c69d62'}));
  const filter = svg('filter',{id:'shadow',x:'-30%',y:'-30%',width:'160%',height:'170%'});
  filter.append(svg('feDropShadow',{dx:'0',dy:'2',stdDeviation:'1.4','flood-color':'#644621','flood-opacity':'.35'}));
  defs.append(gradient,filter); board.append(defs);
  for (let r=0;r<10;r++) board.append(svg('line',{x1:54,y1:57+r*54,x2:486,y2:57+r*54,class:'gridline'}));
  for (let c=0;c<9;c++) {
    if (c===0||c===8) board.append(svg('line',{x1:54+c*54,y1:57,x2:54+c*54,y2:543,class:'gridline'}));
    else for (const [y1,y2] of [[57,273],[327,543]]) board.append(svg('line',{x1:54+c*54,y1,x2:54+c*54,y2,class:'gridline'}));
  }
  board.append(svg('rect',{x:50,y:53,width:440,height:494,class:'gridline outerline'}));
  for (const y of [57,435]) for (const [x1,x2] of [[216,324],[324,216]]) board.append(svg('line',{x1,y1:y,x2,y2:y+108,class:'gridline'}));
  board.append(svg('text',{x:119,y:309,class:'river'},'楚 河'),svg('text',{x:335,y:309,class:'river'},'漢 界'));
  for (let c=0;c<9;c++) board.append(svg('text',{x:54+c*54,y:578,'text-anchor':'middle',class:'coord'},String.fromCharCode(97+(flipped?8-c:c))));
  for (let r=0;r<10;r++) board.append(svg('text',{x:26,y:61+r*54,'text-anchor':'middle',class:'coord'},String(flipped?r+1:10-r)));
  if (!state) return;
  const last = state.moves.at(-1);
  if (last) for (const square of [last.from,last.to]) {
    const [x,y] = point(square); board.append(svg('rect',{x:x-24,y:y-24,width:48,height:48,rx:6,class:'last-square'}));
  }
  for (let square=0;square<90;square++) {
    const [x,y] = point(square), piece = state.board[square];
    if (piece) {
      const group = svg('g',{class:'piece '+(team(piece)===1?'red':'black'),transform:`translate(${x},${y})`});
      group.append(svg('circle',{r:23,class:'disc'}),svg('circle',{r:19.1,class:'rim'}),svg('text',{y:0},GLYPHS[piece]));
      board.append(group);
      if (state.checked && piece === (state.turn===1?'K':'k')) board.append(svg('circle',{cx:x,cy:y,r:25,class:'checked-ring'}));
    }
    if (square === selected) board.append(svg('circle',{cx:x,cy:y,r:25,class:'selected-ring'}));
    if (selected !== null && state.legal.some(([from,to]) => from===selected && to===square)) {
      board.append(svg('circle',{cx:x,cy:y,r:piece?25:6,class:piece?'capture-ring':'legal-dot'}));
    }
  }
  // Transparent hit areas keep all 90 intersections usable by mouse, touch and keyboard.
  for (let square=0;square<90;square++) {
    const [x,y] = point(square), piece = state.board[square];
    const label = `${coord(square)}${piece?' · '+NAMES[piece.toUpperCase()]+' '+(team(piece)===1?'Đỏ':'Đen'): ' · Ô trống'}`;
    const hit = svg('g',{class:'square',role:'button',tabindex:0,'aria-label':label,'aria-pressed':square===selected?'true':'false','data-square':square});
    hit.append(svg('rect',{x:x-26,y:y-26,width:52,height:52,fill:'transparent',rx:5}));
    hit.addEventListener('click',() => selectSquare(square));
    hit.addEventListener('keydown',event => {
      if (event.key==='Enter'||event.key===' ') {event.preventDefault();selectSquare(square);}
      const offsets = {ArrowUp:-9,ArrowDown:9,ArrowLeft:-1,ArrowRight:1};
      if (event.key in offsets) {
        event.preventDefault(); const next = square+offsets[event.key]*(flipped?-1:1);
        if (next>=0&&next<90) board.querySelector(`[data-square="${next}"]`)?.focus();
      }
    }); board.append(hit);
  }
}
function render() {
  drawBoard(); if (!state) return;
  const whose = state.turn===1?'Đỏ':'Đen';
  let title = `Lượt quân ${whose}`;
  let detail = state.mode==='ai'?'Chọn quân, tìm nước đi của bạn.':'Hai người luân phiên trên cùng bàn cờ.';
  if (state.mode==='ai' && state.analysis) {
    const a=state.analysis, elapsed=(a.milliseconds/1000).toFixed(1);
    detail=a.iterations?`${a.name}: ${a.iterations} lần lặp, ${a.nodes} nút, ${elapsed} giây.`:`${a.name}: sâu ${a.depth}, ${a.nodes} nút, ${elapsed} giây.`;
  }
  if (finished()) { title=state.draw?'Ván cờ hòa':`Quân ${state.winner===1?'Đỏ':'Đen'} thắng`;detail=state.draw?'Thế cờ đã lặp lại ba lần.':'Đối phương không còn nước đi hợp lệ.'; }
  else if (busy&&aiTurn()) {title='Máy đang suy nghĩ…';detail='Đang tìm nước đi cho quân '+whose+'.';}
  else if (state.checked) {title=`Quân ${whose} bị chiếu!`;detail='Hãy bảo vệ Tướng bằng một nước hợp lệ.';}
  $('status').textContent=title; $('status-detail').textContent=detail;
  $('status-dot').className=(state.turn===-1?'black ':'')+(busy?'busy':'');
  $('move-count').textContent=String(state.moves.length).padStart(2,'0');
  $('piece-count').textContent=state.board.filter(Boolean).length;
  for (const [location,player] of [['top',flipped?1:-1],['bottom',flipped?-1:1]]) {
    const name = state.mode==='local'?'Người chơi '+(player===1?'Đỏ':'Đen'):(player===state.human?'Bạn':'Máy tính · '+(state.engine||'AI'));
    $(location+'-name').textContent=name;
    $(location+'-detail').textContent='Quân '+(player===1?'Đỏ · đi trước':'Đen');
    const avatar = document.querySelector('.'+location+'-player .avatar');
    avatar.textContent=player===1?'帥':'將'; avatar.className='avatar '+(player===1?'red':'black');
    const active = !finished()&&state.turn===player;
    $(location+'-turn').textContent=finished()?'Kết thúc':active?(busy&&aiTurn()?'Đang suy nghĩ':'Đến lượt'):'Đang chờ';
    $(location+'-turn').className='turn-tag'+(active?' active':'');
  }
  $('new-game').disabled=busy; $('undo').disabled=busy||state.moves.length===0;
  $('settings-fields').disabled=busy;
  $('history-count').textContent=state.moves.length+' nước';
  const history=$('history'); history.replaceChildren();
  if (!state.moves.length) { const li=document.createElement('li');li.className='empty-history';li.innerHTML='<span>棋</span><p>Mỗi ván cờ bắt đầu<br>từ một nước đi.</p>';history.append(li); }
  for (const [i,move] of state.moves.entries()) {
    const li=document.createElement('li');li.className='move-row';
    const num=document.createElement('span');num.className='move-number';num.textContent=String(i+1).padStart(2,'0');
    const piece=document.createElement('span');piece.className='move-piece '+(team(move.piece)===1?'red-text':'black-text');piece.textContent=GLYPHS[move.piece];
    const text=document.createElement('span');text.textContent=`${coord(move.from)} ${move.captured?'×':'–'} ${coord(move.to)}`;
    const note=document.createElement('small');note.textContent=move.captured?'Ăn '+NAMES[move.captured.toUpperCase()]:NAMES[move.piece.toUpperCase()];
    li.append(num,piece,text,note);history.append(li);
  }
  history.scrollTop=history.scrollHeight;
  $('captured').replaceChildren();const captures=state.moves.filter(m=>m.captured);
  if (!captures.length) $('captured').textContent='Chưa có quân bị bắt';
  for (const move of captures) {const el=document.createElement('span');el.className='captured-piece '+(team(move.captured)===1?'red-text':'black-text');el.textContent=GLYPHS[move.captured];el.title=NAMES[move.captured.toUpperCase()];$('captured').append(el);}
}
async function run(action,payload) {
  if (busy) return;
  busy=true;selected=null;render();
  try {
    state=await request(action,{...payload,revision:state?.revision});render();
    if (aiTurn()) {state=await request('ai',{revision:state.revision});}
  } catch(error) {notify(error.message);try {state=await request('state');}catch { /* retain last rendered board */ }}
  finally {busy=false;render();}
}
function selectSquare(square) {
  if (!state||busy||finished()||aiTurn()) return;
  if (selected!==null&&state.legal.some(([from,to])=>from===selected&&to===square)) {run('move',{move:[selected,square]});return;}
  selected=selected===square?null:team(state.board[square])===state.turn?square:null;
  drawBoard();$('board').querySelector(`[data-square="${square}"]`)?.focus();
}
$('mode').addEventListener('change',()=>{$('ai-settings').hidden=$('mode').value==='local';});
function startNew() {
  flipped=$('mode').value==='ai'&&$('human').value==='-1';
  run('new',{mode:$('mode').value,human:Number($('human').value),difficulty:$('difficulty').value,agent:$('agent').value});
}
$('new-game').addEventListener('click',()=>{
  if (state?.moves.length&&!finished()) $('new-dialog').showModal();
  else startNew();
});
$('cancel-new').addEventListener('click',()=>$('new-dialog').close());
$('confirm-new').addEventListener('click',()=>{$('new-dialog').close();startNew();});
$('undo').addEventListener('click',()=>run('undo',{}));
$('flip').addEventListener('click',()=>{flipped=!flipped;render();});
$('help').addEventListener('click',()=>$('help-dialog').showModal());
document.querySelectorAll('.close-dialog,.close-help').forEach(el=>el.addEventListener('click',()=>$('help-dialog').close()));
(async()=>{
  try {
    state=await request('state');flipped=state.mode==='ai'&&state.human===-1;
    $('mode').value=state.mode;$('human').value=String(state.human);$('difficulty').value=state.difficulty;$('agent').value=state.agent||'minimax';
    $('ai-settings').hidden=state.mode==='local';render();
    if (aiTurn()) await run('ai',{});
  } catch(error) {notify('Không kết nối được máy chủ. Hãy tải lại trang.');$('status').textContent='Mất kết nối';$('new-game').disabled=true;}
})();
