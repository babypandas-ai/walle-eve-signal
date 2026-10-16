"""Self-contained interactive HTML replay of a mission (no server, no CDN):
scrub through every decision and watch the belief, paths, evidence and the
agent's reasoning evolve."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np

from .viz import CLUE_CHAR, MODE_COLOR, ROBOT_COLORS


def _q(pm: np.ndarray) -> str:
    """Belief -> base64 of uint8 (sqrt-scaled so faint mass stays visible)."""
    v = np.sqrt(pm / max(pm.max(), 1e-12))
    return base64.b64encode(np.round(v * 255).astype(np.uint8).tobytes()).decode()


def write_replay(path, cfg, agent, frames, trace_path, report):
    steps = [json.loads(line) for line in open(trace_path)]
    steps = [r for r in steps if r["type"] == "step"]
    names = getattr(agent, "robot_names", None) or ["WALL-E"]
    start_pos = {n: list(t[0][0]) for n, t in zip(names, [p[0] for p in _paths(agent)])}
    data = {
        "name": cfg.name, "agent": agent.name, "W": cfg.width, "H": cfg.height,
        "grid": ["".join(r) for r in cfg.grid],
        "chargers": [list(c) for c in cfg.chargers],
        "eve": list(cfg.eve_position), "eveStatus": cfg.eve_status,
        "decoys": [list(d["position"]) for d in cfg.decoys],
        "clues": [{"id": c["id"], "type": c["type"], "pos": list(c["position"]), "ch": CLUE_CHAR[c["type"]]}
                  for c in cfg.clues],
        "found": {e["id"]: e["t"] for e in agent.evidence if e["id"] != "contact"},
        "robots": names, "robotColors": ROBOT_COLORS, "modeColors": MODE_COLOR,
        "start": start_pos,
        "budget": cfg.time_budget, "capacity": cfg.battery_capacity,
        "frames": [_q(f[1]) for f in frames],
        "steps": [{
            "t": r["t"], "robot": r.get("robot", names[0]), "mode": r["mode"], "action": r["action"],
            "pos": r["observation"]["position"], "battery": r["battery"],
            "reasoning": r["decision"]["reasoning"], "notes": r["belief_update_notes"],
            "signal": r["observation"].get("signal"),
            "belief": r["belief"], "change": r["decision"].get("strategy_change"),
        } for r in steps],
        "report": {"next": report["recommended_next_step"], "outcome": report["outcome"]["end_reason"],
                   "found": report["outcome"]["eve_located_visually"],
                   "estimate": report["inference"]["eve_location"], "status": report["inference"]["status"]},
    }
    html = _TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace(
        "__TITLE__", f"{cfg.name} replay")
    Path(path).write_text(html)


def _paths(agent):
    return agent.paths() if hasattr(agent, "paths") else [(agent.trajectory, None)]


_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f7f6f2;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--line:#e6e5e0;
--open:#fcfcfb;--wall:#4c4c4a;--rubble:#e3d9c2;--belief:42,120,214;--accent:#2a78d6;--clue:#0b0b0b;--eve:#e87ba4;--decoy:#6250d6;--charger:#eda100}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8d8c85;--line:#2c2c2a;
--open:#1f1f1e;--wall:#5d5d5a;--rubble:#4a4434;--belief:57,135,229;--accent:#3987e5;--clue:#f0efec}}
:root[data-theme="dark"]{--bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8d8c85;--line:#2c2c2a;
--open:#1f1f1e;--wall:#5d5d5a;--rubble:#4a4434;--belief:57,135,229;--accent:#3987e5;--clue:#f0efec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:16px 20px 4px}h1{font-size:18px;margin:0}header p{margin:2px 0 0;color:var(--ink2)}
main{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,1fr);gap:16px;padding:12px 20px 24px}
@media (max-width:860px){main{grid-template-columns:1fr;padding:12px 16px}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px}
canvas{width:100%;height:auto;display:block;border-radius:6px}
.controls{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
button{background:var(--accent);color:#fff;border:0;border-radius:6px;padding:6px 12px;font:inherit;cursor:pointer}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
input[type=range]{flex:1;min-width:140px;accent-color:var(--accent)}
.k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em;margin:10px 0 4px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.stat b{display:block;font-size:18px;font-variant-numeric:tabular-nums}
.stat span{color:var(--ink2);font-size:12px}
ul{margin:0;padding-left:18px}li{margin:2px 0}
.bar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--ink2)}.bar i{flex:1;height:8px;background:var(--line);border-radius:4px;overflow:hidden}
.bar i u{display:block;height:100%;background:var(--accent);text-decoration:none}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;color:#fff;font-size:12px}
.legend{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;color:var(--ink2);font-size:12px}.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px;background:var(--c)}
.change{border-left:3px solid var(--charger);padding-left:8px}
</style></head><body>
<header><h1 id="title"></h1><p id="sub"></p></header>
<main>
<section class="card">
 <canvas id="cv"></canvas>
 <div class="controls">
  <button id="play">Play</button><button class="ghost" id="prev">&#8592;</button><button class="ghost" id="next">&#8594;</button>
  <input type="range" id="slider" min="0" value="0" aria-label="step">
  <select id="speed" class="ghost" aria-label="speed"><option value="300">slow</option><option value="120" selected>normal</option><option value="40">fast</option></select>
  <label style="color:var(--ink2);font-size:13px"><input type="checkbox" id="truth"> show hidden truth</label>
 </div>
 <div class="legend" id="legend"></div>
</section>
<section class="card" id="panel">
 <div class="stats"><div class="stat"><b id="sT"></b><span>time</span></div><div class="stat"><b id="sB"></b><span>battery (actor)</span></div><div class="stat"><b id="sH"></b><span>entropy (nats)</span></div></div>
 <div class="k">Actor &amp; action</div><div id="act"></div>
 <div class="k">Reasoning</div><ul id="why"></ul>
 <div class="k">What it learned</div><ul id="notes"></ul>
 <div class="k">Status belief</div><div id="status"></div>
 <div class="k">Evidence so far</div><ul id="ev"></ul>
 <div class="k">Final report</div><div id="final" style="color:var(--ink2)"></div>
</section>
</main>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const cv=$('cv'),ctx=cv.getContext('2d');const C=24;cv.width=D.W*C;cv.height=D.H*C;
const frames=D.frames.map(b=>Uint8Array.from(atob(b),c=>c.charCodeAt(0)));
const N=D.steps.length;$('slider').max=N;
$('title').textContent=D.name;$('sub').textContent=`Agent: ${D.agent} · ${N} decisions · drag the slider or press Play`;
const robotColor=n=>D.robotColors[D.robots.indexOf(n)%D.robotColors.length];
$('legend').innerHTML=[...D.robots.map(n=>`<span style="--c:${robotColor(n)}">${n}</span>`),
 '<span style="--c:rgb('+css('--belief')+')">belief (darker = likelier)</span>','<span style="--c:var(--clue)">clue found</span>',
 '<span style="--c:var(--charger)">charger</span>','<span style="--c:var(--eve)">EVE (truth)</span>','<span style="--c:var(--decoy)">decoy (truth)</span>'].join('');
function paths(k){const P={};D.robots.forEach(n=>P[n]=[D.start[n]]);for(let i=0;i<k;i++){const s=D.steps[i];const p=P[s.robot];const l=p[p.length-1];if(l[0]!==s.pos[0]||l[1]!==s.pos[1])p.push(s.pos)}return P}
function draw(k){
 const g=D.grid,truth=$('truth').checked,f=frames[Math.min(k,frames.length-1)],bel=css('--belief');
 for(let y=0;y<D.H;y++)for(let x=0;x<D.W;x++){const ch=g[y][x];ctx.fillStyle=ch==='#'?css('--wall'):ch==='~'?css('--rubble'):css('--open');ctx.fillRect(x*C,y*C,C,C);
  const v=f[y*D.W+x]/255;if(v>0.02&&ch!=='#'){ctx.fillStyle=`rgba(${bel},${(v*0.85).toFixed(3)})`;ctx.fillRect(x*C,y*C,C,C)}}
 const t=k>0?D.steps[k-1].t:0;
 D.chargers.forEach(([x,y])=>{ctx.fillStyle=css('--charger');ctx.fillRect(x*C+5,y*C+5,C-10,C-10)});
 D.clues.forEach(c=>{const ft=D.found[c.id];const got=ft!==undefined&&ft<=t;if(!got&&!truth)return;
  ctx.save();ctx.translate(c.pos[0]*C+C/2,c.pos[1]*C+C/2);ctx.rotate(Math.PI/4);ctx.fillStyle=got?css('--clue'):'transparent';ctx.strokeStyle=got?css('--surface'):css('--muted');ctx.lineWidth=2;
  ctx.fillRect(-6,-6,12,12);ctx.strokeRect(-6,-6,12,12);ctx.restore()});
 if(truth){D.decoys.forEach(([x,y])=>{ctx.strokeStyle=css('--decoy');ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x*C+6,y*C+6);ctx.lineTo(x*C+C-6,y*C+C-6);ctx.moveTo(x*C+C-6,y*C+6);ctx.lineTo(x*C+6,y*C+C-6);ctx.stroke()});
  star(D.eve[0]*C+C/2,D.eve[1]*C+C/2)}
 const P=paths(k);
 Object.entries(P).forEach(([n,p])=>{ctx.strokeStyle=robotColor(n);ctx.lineWidth=3;ctx.lineJoin=ctx.lineCap='round';ctx.beginPath();
  p.forEach(([x,y],i)=>i?ctx.lineTo(x*C+C/2,y*C+C/2):ctx.moveTo(x*C+C/2,y*C+C/2));ctx.stroke();
  const [x,y]=p[p.length-1];ctx.fillStyle=robotColor(n);ctx.strokeStyle=css('--surface');ctx.lineWidth=2;ctx.beginPath();ctx.arc(x*C+C/2,y*C+C/2,7,0,7);ctx.fill();ctx.stroke()});
 if(k>0){const s=D.steps[k-1];if(s.signal&&s.signal.detected){const [x,y]=s.pos,a=(s.signal.bearing_deg-90)*Math.PI/180;
  ctx.strokeStyle=robotColor(s.robot);ctx.setLineDash([5,5]);ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x*C+C/2,y*C+C/2);ctx.lineTo(x*C+C/2+Math.cos(a)*C*6,y*C+C/2+Math.sin(a)*C*6);ctx.stroke();ctx.setLineDash([])}}
 panel(k)}
function star(cx,cy){ctx.fillStyle=css('--eve');ctx.strokeStyle=css('--ink');ctx.lineWidth=1;ctx.beginPath();for(let i=0;i<10;i++){const r=i%2?4:10,a=i*Math.PI/5-Math.PI/2;ctx.lineTo(cx+r*Math.cos(a),cy+r*Math.sin(a))}ctx.closePath();ctx.fill();ctx.stroke()}
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function panel(k){
 const s=k>0?D.steps[k-1]:null;
 $('sT').textContent=s?`${s.t}/${D.budget}`:`0/${D.budget}`;$('sB').textContent=s?s.battery.toFixed(0):'-';$('sH').textContent=s?s.belief.entropy.toFixed(2):'-';
 if(!s){$('act').innerHTML='Mission start: belief initialised from the stale signal.';$('why').innerHTML=$('notes').innerHTML=$('status').innerHTML='';}
 else{const a=s.action.type+(s.action.dir?' '+s.action.dir:'');
  $('act').innerHTML=`<span class="pill" style="background:${robotColor(s.robot)}">${esc(s.robot)}</span> <span class="pill" style="background:${D.modeColors[s.mode]||'#666'}">${s.mode}</span> <b>${esc(a)}</b> at (${s.pos})`;
  $('why').innerHTML=(s.reasoning.map(r=>`<li>${esc(r)}</li>`).join('')||'<li>-</li>')+(s.change?s.change.map(c=>`<li class="change">Strategy change: ${esc(c.reason)}</li>`).join(''):'');
  $('notes').innerHTML=s.notes.map(r=>`<li>${esc(r)}</li>`).join('')||'<li style="color:var(--muted)">nothing new</li>';
  $('status').innerHTML=Object.entries(s.belief.status).map(([k,v])=>`<div class="bar"><span style="width:72px">${k}</span><i><u style="width:${(v*100).toFixed(0)}%"></u></i><span>${(v*100).toFixed(0)}%</span></div>`).join('')+
   `<div class="bar" style="margin-top:6px">most likely cell (${s.belief.map_cell}) · P(within 1) ${(s.belief.p_within_1*100).toFixed(0)}% · 90% region ${s.belief.cred90_cells} cells</div>`}
 const t=s?s.t:0;const ev=D.clues.filter(c=>D.found[c.id]!==undefined&&D.found[c.id]<=t);
 $('ev').innerHTML=ev.map(c=>`<li>t=${D.found[c.id]}: ${c.type.replace('_',' ')} at (${c.pos})</li>`).join('')||'<li style="color:var(--muted)">none yet</li>';
 $('final').innerHTML=`${D.report.found?'EVE located':'EVE not confirmed'} · estimate (${D.report.estimate}), ${D.report.status}<br>${esc(D.report.next)}`;
 $('slider').value=k}
let k=0,timer=null;
function go(n){k=Math.max(0,Math.min(N,n));draw(k)}
$('slider').oninput=e=>go(+e.target.value);$('prev').onclick=()=>go(k-1);$('next').onclick=()=>go(k+1);
$('truth').onchange=()=>draw(k);
$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;$('play').textContent='Play';return}
 if(k>=N)k=0;$('play').textContent='Pause';timer=setInterval(()=>{if(k>=N){clearInterval(timer);timer=null;$('play').textContent='Play';return}go(k+1)},+$('speed').value)};
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')go(k+1);if(e.key==='ArrowLeft')go(k-1);if(e.key===' '){e.preventDefault();$('play').click()}});
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>draw(k));
go(+((location.hash.match(/step=(\d+)/)||[])[1]||0));
if(/truth/.test(location.hash)){$('truth').checked=true;draw(k)}
</script></body></html>
"""
