// ============================================================
//  COPA UNASP 2026 — JS Compartilhado (admin + telão)
//  Toda renderização, utilitários e polling
// ============================================================

// ── Estado global (preenchido via API) ──────────────────────
const estado = {
  craques:         [],
  historicoGlobal: [],
  ultimaCompra:    null,
};

// ── Config ───────────────────────────────────────────────────
const SALDO_INICIAL  = 100000;
const POLL_INTERVAL  = 6000;   // ms

// ── Utilitários ──────────────────────────────────────────────
function fmt(valor) {
  return new Intl.NumberFormat("pt-BR").format(valor) + " cr";
}

function pct(saldo) {
  return (saldo / SALDO_INICIAL) * 100;
}

function corSaldo(saldo) {
  const p = pct(saldo);
  if (p <= 0)  return "#e74c3c";
  if (p <= 20) return "#e74c3c";
  if (p <= 50) return "#f39c12";
  return "#2ecc71";
}

function classeSaldo(saldo) {
  const p = pct(saldo);
  if (p <= 0)  return "saldo-zerado";
  if (p <= 20) return "saldo-critico";
  if (p <= 50) return "saldo-alerta";
  return "saldo-ok";
}

function posIcon(pos) {
  if (pos === "Goleiro") return "🧤";
  if (pos === "Fixo")    return "🧱";
  if (pos === "Ala")     return "⚡";
  if (pos === "Pivô")    return "🎯";
  return "⚽";
}

function posClass(pos) {
  if (!pos) return "";
  const map = { "Goleiro": "pos-goleiro", "Fixo": "pos-fixo", "Ala": "pos-ala", "Pivô": "pos-pivo" };
  return map[pos] || "";
}

function horaStr(ts) {
  const d = new Date(ts);
  return isNaN(d) ? "—" : d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// ── Toast ─────────────────────────────────────────────────────
function toast(msg, tipo = "ok") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast toast-${tipo}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.remove(), 400);
  }, 3500);
}

// ── Indicador de conexão ─────────────────────────────────────
function setConn(ok) {
  const dot = document.querySelector(".conn-dot");
  const lbl = document.querySelector(".conn-label");
  if (!dot) return;
  dot.classList.toggle("off", !ok);
  if (lbl) lbl.textContent = ok ? "Conectado" : "Sem conexão";
}

// ── Stats Bar ─────────────────────────────────────────────────
function renderStats() {
  const c = estado.craques;
  if (!c.length) return;

  const totalGasto    = c.reduce((a, x) => a + (SALDO_INICIAL - x.saldo), 0);
  const totalJog      = estado.historicoGlobal.length;
  const mediaSaldo    = Math.round(c.reduce((a, x) => a + x.saldo, 0) / c.length);
  const lider         = c.reduce((a, b) => a.saldo > b.saldo ? a : b);

  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set("stat-total-gastos",    fmt(totalGasto));
  set("stat-total-jogadores", totalJog);
  set("stat-media-saldo",     fmt(mediaSaldo));
  set("stat-lider",           totalJog > 0 ? `${lider.nome} (${lider.selecao})` : "—");
}

// ── Cartões ───────────────────────────────────────────────────
function renderCartoes(selecionadoId = null, onSelecionar = null) {
  const grid = document.getElementById("grid-craques");
  if (!grid) return;
  grid.innerHTML = "";

  // Agrupar jogadores por craque
  const jogPorCraque = {};
  estado.historicoGlobal.forEach(c => {
    if (!jogPorCraque[c.craque_id]) jogPorCraque[c.craque_id] = [];
    jogPorCraque[c.craque_id].push(c);
  });

  estado.craques.forEach((cr, i) => {
    const p       = pct(cr.saldo);
    const cor     = corSaldo(cr.saldo);
    const cls     = classeSaldo(cr.saldo);
    const jogList = (jogPorCraque[cr.id] || []).slice().reverse(); // mais recente primeiro
    const gasto   = SALDO_INICIAL - cr.saldo;

    const jogHTML = jogList.length === 0
      ? `<p class="sem-jogadores">Nenhum jogador ainda</p>`
      : jogList.map(j => `
          <div class="jogador-item">
            <span class="jogador-nome">${posIcon(j.posicao)} ${j.jogador}</span>
            <div class="jogador-right">
              <span class="badge-pos ${posClass(j.posicao)}">${j.posicao || "—"}</span>
              <span class="jogador-valor">${fmt(j.valor)}</span>
            </div>
          </div>`).join("");

    const isSel = selecionadoId === cr.id;

    const card = document.createElement("div");
    card.className = `craque-card ${cls}${isSel ? " selecionado" : ""}`;
    card.dataset.id = cr.id;
    card.style.setProperty("--cor-sel", cr.cor);
    card.style.setProperty("--cor-sec", cr.cor_sec);


    card.innerHTML = `
      <div class="card-header">
        <div class="bandeira-circle">
          <img src="${cr.bandeira}" alt="${cr.selecao}" onerror="this.style.display='none'" />
        </div>
        <div class="card-info">
          <h3 class="craque-nome">${cr.nome}</h3>
          <p class="craque-selecao">${cr.selecao}</p>
        </div>
        <div class="card-badge">#${cr.id}</div>
      </div>
      <div class="saldo-section">
        <span class="saldo-label">Saldo disponível</span>
        <span class="saldo-valor" style="color:${cor}">${fmt(cr.saldo)}</span>
        <div class="barra-saldo">
          <div class="barra-fill" style="width:${Math.max(0,p)}%;background:${cor}"></div>
        </div>
        <span class="saldo-pct">${p.toFixed(1)}% restante</span>
      </div>
      <div class="jogadores-section">
        <h4 class="jogadores-titulo">
          <span>Elenco (${jogList.length})</span>
          <span class="total-gasto">${fmt(gasto)} gastos</span>
        </h4>
        <div class="jogadores-lista">${jogHTML}</div>
      </div>
      ${onSelecionar ? `<button class="btn-selecionar" onclick="(${onSelecionar})(${cr.id})">
        ${isSel ? "✓ Selecionado" : "Selecionar para Compra"}
      </button>` : ""}
    `;

    grid.appendChild(card);
  });
}

// ── Histórico ─────────────────────────────────────────────────
function renderHistorico(filtroNome = "todos") {
  const tbody = document.getElementById("historico-tbody");
  if (!tbody) return;

  let lista = estado.historicoGlobal;
  if (filtroNome !== "todos") lista = lista.filter(h => h.craque === filtroNome);

  if (lista.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="vazio">Nenhuma compra registrada ainda</td></tr>`;
    return;
  }

  tbody.innerHTML = lista.map((h, i) => `
    <tr class="${i % 2 === 0 ? "par" : "impar"}">
      <td><img src="${h.bandeira}" style="width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:6px" />${h.craque}</td>
      <td>${h.selecao}</td>
      <td><strong>${h.jogador}</strong></td>
      <td><span class="badge-pos ${posClass(h.posicao)}">${h.posicao || "—"}</span></td>
      <td class="valor-cell">${fmt(h.valor)}</td>
      <td class="hora-cell">${horaStr(h.timestamp)}</td>
      <td></td>
      <td><button class="btn-desfazer" onclick="desfazerCompra(${h.id}, '${h.jogador.replace(/'/g, "\\'")}')">Desfazer</button></td>
    </tr>`).join("");
}

// ── Relatório Final ───────────────────────────────────────────
function gerarRelatorio() {
  const agora   = new Date().toLocaleString("pt-BR", { day:"2-digit", month:"2-digit", year:"numeric", hour:"2-digit", minute:"2-digit" });
  const total   = estado.craques.reduce((a, c) => a + (SALDO_INICIAL - c.saldo), 0);
  const totalJ  = estado.historicoGlobal.length;
  const rico    = [...estado.craques].sort((a,b) => b.saldo - a.saldo)[0];
  const gastou  = [...estado.craques].sort((a,b) => (SALDO_INICIAL - b.saldo) - (SALDO_INICIAL - a.saldo))[0];
  const maisJog = [...estado.craques].sort((a,b) => {
    const la = estado.historicoGlobal.filter(h => h.craque_id === a.id).length;
    const lb = estado.historicoGlobal.filter(h => h.craque_id === b.id).length;
    return lb - la;
  })[0];

  const L = "═".repeat(48);
  const l = "─".repeat(48);
  let t = `${L}\n       ⚽  COPA UNASP 2026 — LEILÃO FINAL  ⚽\n${L}\n`;
  t += `  📅 Data: ${agora}\n${l}\n\n`;
  t += `📊 RESUMO GERAL\n${l}\n`;
  t += `  💰 Total movimentado : ${fmt(total)}\n`;
  t += `  ⚽ Jogadores leiloados: ${totalJ}\n`;
  t += `  🏆 Mais rico          : ${rico.nome} (${rico.selecao}) (${fmt(rico.saldo)} restante)\n`;
  t += `  🛒 Mais gastou        : ${gastou.nome} (${gastou.selecao}) (${fmt(SALDO_INICIAL - gastou.saldo)} gastos)\n`;
  const njMais = estado.historicoGlobal.filter(h => h.craque_id === maisJog.id).length;
  t += `  📋 Maior elenco       : ${maisJog.nome} (${maisJog.selecao}) (${njMais} jogador${njMais !== 1 ? "es" : ""})\n\n`;
  t += `${L}\n           🗂️  ELENCOS POR CRAQUE\n${L}\n\n`;

  const ord = [...estado.craques].sort((a,b) => (SALDO_INICIAL - b.saldo) - (SALDO_INICIAL - a.saldo));
  ord.forEach((cr, idx) => {
    const jogs  = estado.historicoGlobal.filter(h => h.craque_id === cr.id);
    const gasto = SALDO_INICIAL - cr.saldo;
    const med   = ["🥇","🥈","🥉"][idx] || `${idx+1}º`;
    t += `${med} ${cr.nome.toUpperCase()} — ${cr.selecao}\n`;
    t += `   💵 Saldo restante : ${fmt(cr.saldo)} (${pct(cr.saldo).toFixed(1)}%)\n`;
    t += `   💸 Total gasto    : ${fmt(gasto)}\n`;
    t += `   👥 Jogadores (${jogs.length})\n`;
    if (!jogs.length) { t += `      • Nenhum jogador\n`; }
    else jogs.slice().reverse().forEach(j => {
      const pos = j.posicao ? `[${j.posicao}]`.padEnd(10) : "          ";
      t += `      • ${pos} ${j.jogador.padEnd(20)} ${fmt(j.valor)}\n`;
    });
    t += `\n`;
  });

  t += `${L}\n    Sistema de Leilão — Copa UNASP 2026 ⚽\n${L}\n`;
  return t;
}

function abrirRelatorio() {
  document.getElementById("relatorio-texto").textContent = gerarRelatorio();
  document.getElementById("copiado-msg").style.opacity = "0";
  document.getElementById("modal-relatorio").classList.add("ativo");
  document.body.style.overflow = "hidden";
}
function fecharRelatorio() {
  document.getElementById("modal-relatorio").classList.remove("ativo");
  document.body.style.overflow = "";
}
function fecharModalFora(e) { if (e.target.id === "modal-relatorio") fecharRelatorio(); }
function copiarRelatorio() {
  navigator.clipboard.writeText(document.getElementById("relatorio-texto").textContent).then(() => {
    const m = document.getElementById("copiado-msg");
    m.style.opacity = "1";
    setTimeout(() => m.style.opacity = "0", 2500);
  });
}

// ── Chart (bar) ───────────────────────────────────────────────
let chartInstance = null;
function renderChart() {
  const ctx = document.getElementById("chart-saldos");
  if (!ctx || !window.Chart) return;
  const labels = estado.craques.map(c => c.nome);
  const dados  = estado.craques.map(c => c.saldo);
  const cores  = estado.craques.map(c => corSaldo(c.saldo));

  if (chartInstance) {
    chartInstance.data.datasets[0].data            = dados;
    chartInstance.data.datasets[0].backgroundColor = cores;
    chartInstance.update("none");
    return;
  }
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Saldo", data: dados, backgroundColor: cores, borderRadius: 7, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => fmt(ctx.raw) } } },
      scales: {
        x: { ticks: { color: "#8896C4", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { min: 0, max: SALDO_INICIAL,
             ticks: { color: "#8896C4", callback: v => (v/1000).toFixed(0)+"k" },
             grid: { color: "rgba(255,255,255,0.08)" } }
      }
    }
  });
}
