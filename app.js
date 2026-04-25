const API_BASE = window.FL_STRIKE_API || "http://127.0.0.1:5000";
const fmt = (n, d=2) => Number(n ?? 0).toLocaleString('en-US', {maximumFractionDigits:d, minimumFractionDigits:d});
const pct = (n) => `${Number(n ?? 0) >= 0 ? '+' : ''}${fmt(n)}%`;
const cls = (n) => Number(n ?? 0) > 0 ? 'pos' : Number(n ?? 0) < 0 ? 'neg' : 'warn';

function setText(id, value){ const el=document.getElementById(id); if(el) el.textContent=value ?? '--'; }
function badge(text){ return `<span class="badge">${text ?? '--'}</span>`; }
function scoreClass(score){ return score >= 80 ? 'pos' : score >= 60 ? 'warn' : 'neg'; }

function renderRows(id, rows, type){
  const tbody = document.getElementById(id);
  if(!tbody) return;
  tbody.innerHTML = rows.map(r => {
    if(type === 'market') return `<tr><td>${r.symbol}</td><td>${fmt(r.price)}</td><td class="${cls(r.change_pct)}">${pct(r.change_pct)}</td><td>${fmt(r.rvol)}</td><td>${badge(r.change_pct > 0 ? 'داعم' : 'ضاغط')}</td></tr>`;
    if(type === 'sector') return `<tr><td>${r.symbol}</td><td>${fmt(r.price)}</td><td class="${cls(r.change_pct)}">${pct(r.change_pct)}</td><td>${fmt(r.rvol)}</td><td>${badge(r.change_pct > 1 ? 'قائد' : r.change_pct > 0 ? 'داعم' : 'ضعيف')}</td></tr>`;
    if(type === 'leader') return `<tr><td><strong>${r.symbol}</strong></td><td>${r.sector}</td><td>${fmt(r.price)}</td><td class="${cls(r.change_pct)}">${pct(r.change_pct)}</td><td>${fmt(r.rvol)}</td><td>${badge(r.stage)}</td><td>${r.move_type}</td><td>${r.flow}</td><td class="score ${scoreClass(r.score)}">${r.score}</td><td>${badge(r.status)}</td></tr>`;
    return `<tr><td><strong>${r.symbol}</strong></td><td>${fmt(r.price)}</td><td class="${cls(r.change_pct)}">${pct(r.change_pct)}</td><td>${fmt(r.rvol)}</td><td>${pct(r.gap_pct)}</td><td>${badge(r.stage)}</td><td>${r.reentry}</td><td>${r.move_type}</td><td>${r.risk}</td><td class="score ${scoreClass(r.score)}">${r.score}</td><td>${badge(r.status)}</td></tr>`;
  }).join('');
}

function renderList(id, items, kind){
  const el=document.getElementById(id);
  if(!el) return;
  if(!items || !items.length){ el.innerHTML = `<div class="item">لا توجد بيانات الآن</div>`; return; }
  el.innerHTML = items.slice(0,10).map(x => {
    if(kind === 'news') return `<div class="item"><strong>${x.symbol || 'خبر'}</strong><span>${x.headline || ''}</span><br><span>المصدر: ${x.source || '--'}</span></div>`;
    return `<div class="item"><strong>${x.symbol || '--'}</strong><span>${x.title || 'رمز متداول اجتماعيًا'} — ${x.source || '--'}</span></div>`;
  }).join('');
}

function render(data){
  const c = data.clock || {};
  setText('date', c.date); setText('day', c.day); setText('riyadhTime', c.riyadh_time); setText('nyTime', c.ny_time); setText('marketStatus', c.status);
  const imp = data.impression || {};
  setText('impIntent', imp.market_intent); setText('impMood', imp.mood); setText('impLiquidity', imp.liquidity); setText('impCatalyst', imp.catalyst);
  setText('impSentiment', imp.sentiment); setText('impFlow', imp.flow_proxy); setText('judgment', imp.judgment); setText('dataNote', data.data_note);
  setText('confidence', `الثقة: ${data.market?.confidence ?? '--'}%`);
  setText('lastUpdate', `آخر تحديث: ${new Date(data.updated_at).toLocaleString('ar-SA')}`);
  const chips = document.getElementById('trendChips');
  chips.innerHTML = [...(imp.strongest_symbols || []), ...(imp.trend_symbols || [])].filter(Boolean).slice(0,10).map(s => `<span class="chip">${s}</span>`).join('');
  renderRows('marketRows', data.market_rows || [], 'market');
  renderRows('sectorRows', data.sectors || [], 'sector');
  renderRows('leaderRows', data.leaders || [], 'leader');
  renderRows('smallRows', data.smallcaps || [], 'small');
  renderList('socialList', data.trends || [], 'social');
  renderList('newsList', data.news || [], 'news');
}

async function loadDashboard(){
  setText('judgment', 'جاري سحب البيانات الحقيقية...');
  try{
    const res = await fetch(`${API_BASE}/api/dashboard`);
    if(!res.ok) throw new Error(`API Error ${res.status}`);
    const data = await res.json();
    if(data.error) throw new Error(data.error);
    render(data);
  }catch(err){
    setText('judgment', `فشل الاتصال بالـ Backend: ${err.message}. شغل backend/app.py أو عدل API_BASE في app.js بعد نشره على Render.`);
  }
}

document.getElementById('refreshBtn').addEventListener('click', loadDashboard);
loadDashboard();
setInterval(loadDashboard, 180000);
