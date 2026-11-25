"use strict";

const data = globalThis.commerceEvidence;
const form = document.querySelector("#brief-form");
const input = document.querySelector("#scene");
const market = document.querySelector("#market");
const keywords = document.querySelector("#keywords");
const result = document.querySelector("#result");
const announcement = document.querySelector("#announcement");
const modeStatus = document.querySelector("#mode-status");
const runButton = document.querySelector("#run-button");
const localFile = location.protocol === "file:";
const sampleInput = "我想找一个适合小批量试卖、让宠物喂食区更整洁的商品方向。";
const examples = ["狗狗喝水后地面容易积水，想找方便倒水的商品。", "想找容易清洗的宠物餐垫。", "想找耐用、边缘不容易被啃坏的宠物餐垫。"];
const featureColumns = ["catch", "ownBowl", "washable", "drain", "liftOut"];
let activeRequest = null;

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[char]);
}

function sourceLink(url, label) {
  let destination;
  try {
    destination = new URL(url);
  } catch {
    return escapeHTML(label);
  }
  if (destination.protocol !== "https:") return escapeHTML(label);
  return `<a href="${escapeHTML(destination.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(label)}</a>`;
}

function formatDate(date, dateOnly = true) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium", ...(dateOnly ? {timeZone: "UTC"} : {timeStyle: "short"}),
  }).format(new Date(date));
}

function setReport(content, message) {
  result.innerHTML = content;
  document.querySelectorAll("nav a").forEach(link => {
    link.hidden = !document.getElementById(link.hash.slice(1));
  });
  announcement.textContent = message;
}

function evidenceList(records) {
  if (!records.length) return '<p class="subtle">样本中暂无买家反馈。</p>';
  return `<ul class="evidence-list">${records.map(item => {
    const product = data.products.find(entry => entry.id === item.product);
    const counter = item.stance === "counter";
    return `<li class="${counter ? "counter" : "support"}">
      <p><strong>${counter ? "反例" : "买家反馈"}</strong> · ${escapeHTML(zh.reviews[item.id] || item.note)}</p>
      <span class="subtle">${sourceLink(item.url, `原文：${item.title}`)} · ${escapeHTML(product.name)} · ${formatDate(item.date)}</span>
    </li>`;
  }).join("")}</ul>`;
}

function candidateReason(candidate) {
  if (candidate.status === "covered") return `样本中已有 ${candidate.direct.length} 个替代品覆盖这组功能。`;
  return zh.directions[candidate.id][2] || "现有反馈不足以支撑这个商品方向。";
}

function candidateRows(candidates) {
  return candidates.map(candidate => {
    const [title, audience, , next] = zh.directions[candidate.id];
    return `<details><summary>
      <span class="direction">${title}</span><span class="next-summary">${candidateReason(candidate)}</span>
      <span class="status ${candidate.status}">${zh.status[candidate.status]}</span>
    </summary><div class="detail-body">
      <p><strong>目标买家</strong> ${audience}</p>
      <p><strong>待验证功能</strong> ${candidate.features.map(key => zh.features[key]).join("、")}</p>
      <p><strong>替代品</strong> ${[...candidate.direct, ...candidate.partial].map(product => sourceLink(product.url, product.name)).join("、") || "样本里暂无线索。"}</p>
      <p><strong>下一步</strong> ${next}</p>${evidenceList(candidate.evidence)}
    </div></details>`;
  }).join("");
}

function featureCell(value) {
  if (value === true) return '<td class="yes">有</td>';
  if (value === false) return "<td>无</td>";
  return '<td class="unknown">待核实</td>';
}

function competitionTable(focusFeatures) {
  const columns = [...new Set([...focusFeatures, ...featureColumns])];
  return `<div class="table-wrap" tabindex="0" role="region" aria-label="竞品功能矩阵">
    <table aria-label="公开样本的商品功能对比">
      <thead><tr><th scope="col">商品</th>${columns.map(key => `<th scope="col">${zh.features[key]}</th>`).join("")}</tr></thead>
      <tbody>${data.products.map(product => `<tr>
        <th scope="row">${sourceLink(product.url, product.name)}<span class="subtle">${zh.format[product.id]} · ${escapeHTML(product.source)}</span></th>
        ${columns.map(key => featureCell(product.features[key])).join("")}
      </tr>`).join("")}</tbody>
    </table>
  </div>`;
}

function painChart(themes, total) {
  const ordered = [...themes].sort((a, b) => Number(b.focused) - Number(a.focused) || b.supportCount - a.supportCount);
  return ordered.map(theme => `<details class="bar-group"><summary>
    <span>${zh.themes[theme.id]}</span>
    <span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${total ? 100 * theme.supportCount / total : 0}%"></span></span>
    <span class="bar-count">${theme.supportCount}/${total}</span>
  </summary>${evidenceList(theme.records)}</details>`).join("");
}

function renderSample() {
  const report = analyzeProductScene(input.value, data);
  if (!report.covered) {
    setReport(`<section class="empty"><h2>这组离线证据未覆盖此场景</h2>
      <p>样本范围为美国市场的宠物喂食区。其他场景可切换实时检索。</p>
      <button class="example" type="button" data-example="sample">恢复示例</button></section>`, "离线样本未覆盖此场景。");
    return;
  }

  const lead = report.candidates[0];
  const title = zh.directions[lead.id][0];
  setReport(`
    <section class="report-head" aria-label="当前判断">
      <div class="verdict"><span class="status ${lead.status}">${zh.status[lead.status]}</span>
        <h2>${zh.action[lead.status]}：${title}</h2><p>${candidateReason(lead)}</p>
      </div>
      <figure class="reference"><img src="${escapeHTML(data.referenceImage)}" width="88" height="64" alt="Neater Feeder Deluxe 集水底座" referrerpolicy="no-referrer"><figcaption>结构参考<br>${sourceLink(data.products.find(product => product.id === "neater").url, "Neater Feeder 集水槽")}</figcaption></figure>
    </section>
    <dl class="metrics">
      <div><dt>目标市场</dt><dd>美国<small>宠物喂食区</small></dd></div>
      <div><dt>样本最新反馈</dt><dd>${formatDate(report.latestFeedback)}<small>来自收录的买家评论</small></dd></div>
      <div><dt>市场容量</dt><dd>待估<small>缺少该细分品类的销量数据</small></dd></div>
    </dl>
    <section id="opportunities" class="section" aria-labelledby="opportunity-title">
      <div class="section-head"><h2 id="opportunity-title">机会对比</h2><span class="subtle">${report.candidates.length} 个候选方向</span></div>
      <div class="opportunities">${candidateRows(report.candidates)}</div>
    </section>
    <section id="competition" class="section" aria-labelledby="competition-title">
      <div class="section-head"><h2 id="competition-title">竞品功能矩阵</h2><span class="subtle">${data.products.length} 个商品系列</span></div>
      ${competitionTable(lead.features)}
    </section>
    <section id="evidence" class="section visual-grid" aria-labelledby="evidence-title">
      <div><h2 id="evidence-title">买家痛点</h2><p class="subtle">提到该问题的商品系列数 / 有反馈的商品系列数</p>${painChart(report.themes, report.feedbackProductCount)}</div>
      <section class="notes" aria-labelledby="notes-title"><h2 id="notes-title">证据范围</h2>
        <dl><dt>评论样本</dt><dd>${data.period} 年 · ${data.feedback.length} 条评论，覆盖 ${report.feedbackProductCount} 个商品系列，含便携饮水碗作对照。同系列的不同配色合并。</dd>
        <dt>竞品功能</dt><dd>依据公开商品页。待核实项表示没有足够材料判断。</dd>
        <dt>市场容量</dt><dd>需要目标市场和销售渠道的销量数据，或可解释的估算依据。</dd></dl>
      </section>
    </section>
    <div class="examples" aria-label="示例消费场景">${examples.map((example, i) => `<button class="example" type="button" data-example="${i}">${["积水处理", "日常清洁", "餐垫耐用性"][i]}</button>`).join("")}</div>`, `${zh.action[lead.status]}：${title}。`);
  const image = result.querySelector(".reference img");
  image.addEventListener("error", () => image.hidden = true, {once: true});
  if (image.complete && !image.naturalWidth) image.hidden = true;
}

function leadList(entries, emptyText) {
  if (!entries.length) return `<p class="subtle">${emptyText}</p>`;
  return `<ul class="leads">${entries.map(entry => `<li>
    <span class="subtle">${escapeHTML(entry.source)}</span>
    <h3>${sourceLink(entry.url, entry.title)}</h3>
    ${entry.summary ? `<p lang="${/[\u4e00-\u9fff]/.test(entry.summary) ? "zh-CN" : "en"}">${escapeHTML(entry.summary)}</p>` : ""}
  </li>`).join("")}</ul>`;
}

function renderDiscovery(report) {
  const {product, feedback, reference} = report.groups;
  const total = product.length + feedback.length + reference.length;
  const lead = report.themes[0];
  const title = lead ? `优先核查：${zh.themes[lead.id]}` : total ? "补证据后再判断" : "这次未找到可用线索";
  const note = lead ? zh.checks[lead.id] : "先核对商品页和买家反馈，再判断是否有尚未覆盖的需求。";
  setReport(`
    <section id="opportunities" class="report-head" aria-label="当前判断"><div class="verdict">
      <span class="status ${lead ? "research" : "thin"}">${report.state === "partial" ? "部分检索未完成" : "检索线索 · 待核查"}</span>
      <h2>${title}</h2><p>${note}</p>
    </div></section>
    <dl class="metrics">
      <div><dt>目标市场</dt><dd>${zh.market[report.market]}<small>检索地区，以原始页面为准</small></dd></div>
      <div><dt>市场活跃度</dt><dd>待核查<small>缺少可比较的日期序列</small></dd></div>
      <div><dt>市场容量</dt><dd>待估<small>缺少销量或销售额数据</small></dd></div>
    </dl>
    <section id="competition" class="section"><div class="section-head"><h2>竞品线索</h2><span class="subtle">${product.length} 个商品页面 · 规格待核查</span></div>${leadList(product, "本次暂无可识别的商品页。")}</section>
    <section id="evidence" class="section"><div class="section-head"><h2>买家反馈线索</h2><span class="subtle">${feedback.length} 个页面 · 搜索摘要</span></div>
      ${report.themes.map(theme => `<details class="live-theme"><summary>${zh.themes[theme.id]} <span class="subtle">${theme.urls.length} 个页面的摘要提及</span></summary>${leadList(feedback.filter(item => theme.urls.includes(item.url)), "")}</details>`).join("")}
      <details class="live-theme" ${report.themes.length ? "" : "open"}><summary>全部反馈线索</summary>${leadList(feedback, "本次暂无可识别的反馈页。")}</details>
    </section>
    <section class="section"><details class="live-theme"><summary>其他参考 <span class="subtle">${reference.length} 个页面</span></summary>${leadList(reference, "本次暂无其他参考。")}</details>
    <details class="live-theme"><summary>本次检索记录 <span class="subtle">${formatDate(report.searched_at, false)}</span></summary>
      <ul class="search-log">${report.searches.map(search => `<li><strong>${zh.searches[search.kind]}</strong> · ${escapeHTML(search.query)} · ${search.error ? zh.errors[search.error] || "失败" : `返回 ${search.results} 条`}</li>`).join("")}</ul>
    </details></section>`, `${title}。找到 ${total} 个去重后的页面。`);
}

function renderSetup() {
  const context = localFile ? "当前从本地文件打开。实时检索需要通过本地服务访问。" : "本地服务还没有配置检索密钥。";
  setReport(`<section class="empty"><h2>实时检索尚未启用</h2><p>${context}</p>
    <details class="live-theme"><summary>本地启动方式</summary>
      <p>在同一个终端配置环境变量 <code>BRAVE_SEARCH_API_KEY</code>，然后运行 <code>python commerce/server.py</code>，打开终端显示的地址。</p>
    </details><button class="example" type="button" data-example="sample">返回离线样本</button></section>`, "实时检索尚未启用。");
}

async function runDiscovery() {
  if (localFile) return renderSetup();
  const request = new AbortController();
  activeRequest = request;
  runButton.disabled = true;
  runButton.textContent = "检索中…";
  setReport('<section class="empty" aria-busy="true"><h2>正在查找商品和买家反馈</h2></section>', "正在检索。");
  try {
    const response = await fetch("/api/discover", {
      method: "POST", headers: {"Content-Type": "application/json"}, signal: request.signal,
      body: JSON.stringify({scene: input.value.trim(), market: market.value, keywords: keywords.value.trim()}),
    });
    const report = await response.json();
    if (activeRequest !== request) return;
    if (report.error === "unconfigured") return renderSetup();
    if (!response.ok) throw new Error(zh.errors[report.error] || "实时检索失败，请稍后重试。");
    renderDiscovery(report);
  } catch (error) {
    if (activeRequest !== request) return;
    const message = error instanceof TypeError ? "本地服务暂时无法连接。" : error.message;
    setReport(`<section class="empty"><h2>实时检索未完成</h2><p>${escapeHTML(message)}</p></section>`, "实时检索未完成。");
  } finally {
    if (activeRequest === request) {
      activeRequest = null;
      runButton.disabled = false;
      runButton.textContent = "检索市场";
    }
  }
}

function setMode() {
  if (activeRequest) activeRequest.abort();
  activeRequest = null;
  const live = form.elements.mode.value === "live";
  modeStatus.textContent = live ? "实时检索" : "离线样本";
  market.disabled = !live;
  if (!live) market.value = "US";
  document.querySelector("#search-options").hidden = !live;
  runButton.disabled = false;
  runButton.textContent = live ? "检索市场" : "查看机会";
  if (!live) renderSample();
  else if (localFile) renderSetup();
  else setReport('<section class="empty"><h2>等待检索</h2><p>本次使用的目标市场和检索记录将在结果中展示。</p></section>', "实时检索模式。");
}

form.addEventListener("change", event => {
  if (event.target.name === "mode") setMode();
});
form.addEventListener("submit", event => {
  event.preventDefault();
  input.value = input.value.trim();
  if (!form.reportValidity() || activeRequest) return;
  if (form.elements.mode.value === "live") runDiscovery();
  else renderSample();
});
result.addEventListener("click", event => {
  const button = event.target.closest("button[data-example]");
  if (!button) return;
  input.value = button.dataset.example === "sample" ? sampleInput : examples[Number(button.dataset.example)];
  form.querySelector('[value="sample"]').checked = true;
  setMode();
  input.focus();
});

input.value = sampleInput;
setMode();
