const form = document.querySelector("#analysisForm");
const submitButton = document.querySelector("#submitButton");
const healthStatus = document.querySelector("#healthStatus");
const stageText = document.querySelector("#stageText");
const progressBar = document.querySelector("#progressBar");
const logBox = document.querySelector("#logBox");
const results = document.querySelector("#results");
const historyList = document.querySelector("#historyList");
const llmForm = document.querySelector("#llmForm");
const llmStateText = document.querySelector("#llmStateText");
const qrcodeOverlay = document.querySelector("#qrcodeOverlay");
const qrcodeImage = document.querySelector("#qrcodeImage");
const qrcodeTitle = document.querySelector("#qrcodeTitle");
const qrcodeHint = document.querySelector("#qrcodeHint");
const smsCodeSection = document.querySelector("#smsCodeSection");
const smsCodeInput = document.querySelector("#smsCodeInput");
const smsCodeSubmit = document.querySelector("#smsCodeSubmit");

const metricNames = {
  avg_engagement: "平均互动",
  collection_rate: "收藏率",
  comment_rate: "评论率",
  share_rate: "分享率",
  hit_rate: "高表现稳定度",
  avg_text_length: "正文长度",
};

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("服务异常");
    const health = await response.json();
    healthStatus.textContent = health.llm_enabled ? "服务已就绪 · AI 已启用" : "服务已就绪 · 未配置 AI";
    healthStatus.classList.add("ok");
  } catch (error) {
    healthStatus.textContent = "服务未启动";
    healthStatus.classList.add("bad");
  }
}

let currentLlmSettings = {};

async function loadLlmSettings() {
  try {
    const settings = await fetch("/api/settings/llm").then((res) => res.json());
    currentLlmSettings = settings;
    document.querySelector("#llmEnabled").checked = Boolean(settings.enabled);
    document.querySelector("#llmApiKey").value = "";
    llmStateText.textContent = settings.has_api_key ? "已保存 Key" : "未保存 Key";
  } catch (error) {
    llmStateText.textContent = "读取失败";
  }
}

llmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  llmStateText.textContent = "保存中";
  const payload = {
    enabled: document.querySelector("#llmEnabled").checked,
    base_url: currentLlmSettings.base_url || "https://api.openai.com/v1",
    model: currentLlmSettings.model || "gpt-4o-mini",
    api_key: document.querySelector("#llmApiKey").value.trim(),
  };
  try {
    const response = await fetch("/api/settings/llm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("保存失败");
    const settings = await response.json();
    document.querySelector("#llmApiKey").value = "";
    llmStateText.textContent = settings.has_api_key ? "已保存 Key" : "未保存 Key";
    await checkHealth();
  } catch (error) {
    llmStateText.textContent = "保存失败";
  }
});

function valueText(key, value) {
  const num = Number(value || 0);
  if (["collection_rate", "comment_rate", "share_rate", "hit_rate"].includes(key)) {
    return `${(num * 100).toFixed(1)}%`;
  }
  return num.toLocaleString("zh-CN");
}

function renderLogs(logs) {
  logBox.innerHTML = "";
  if (!logs.length) {
    logBox.innerHTML = "<p>等待日志。</p>";
    return;
  }
  for (const line of logs.slice(-120)) {
    const p = document.createElement("p");
    p.textContent = line;
    logBox.appendChild(p);
  }
  logBox.scrollTop = logBox.scrollHeight;
}

function addList(id, items) {
  const list = document.querySelector(id);
  list.innerHTML = "";
  for (const item of items || []) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
}

function renderCompareHero(data) {
  const mine = data.mine;
  const target = data.target;
  const host = document.querySelector("#compareHero");
  host.innerHTML = "";
  host.appendChild(profileCard("我的主页", mine, "mine"));
  host.appendChild(vsCard(data.comparison.metrics.avg_engagement));
  host.appendChild(profileCard("目标用户", target, "target"));
}

function profileCard(title, profile, tone) {
  const card = document.createElement("article");
  card.className = `profile-card ${tone}`;
  const creator = profile.creator || {};
  const overview = profile.overview || {};
  card.innerHTML = `
    <span>${title}</span>
    <h2>${escapeHtml(creator.nickname || title)}</h2>
    <div class="profile-kpis">
      <div><strong>${valueText("fans", overview.fans)}</strong><em>粉丝</em></div>
      <div><strong>${valueText("avg_engagement", overview.avg_engagement)}</strong><em>平均互动</em></div>
      <div><strong>${valueText("hit_rate", overview.hit_rate)}</strong><em>稳定度</em></div>
    </div>
  `;
  return card;
}

function vsCard(avgMetric) {
  const card = document.createElement("article");
  card.className = "vs-card";
  const direction = avgMetric.delta > 0 ? "目标更强" : avgMetric.delta < 0 ? "我方更强" : "基本持平";
  card.innerHTML = `
    <span>综合观感</span>
    <strong>${direction}</strong>
    <em>平均互动差值 ${valueText("avg_engagement", Math.abs(avgMetric.delta))}</em>
  `;
  return card;
}

function renderVisualMetrics(data) {
  const host = document.querySelector("#visualMetrics");
  host.innerHTML = "";
  for (const [key, metric] of Object.entries(data.comparison.metrics)) {
    const mine = Number(metric.mine || 0);
    const target = Number(metric.target || 0);
    const max = Math.max(mine, target, 0.0001);
    const targetWidth = Math.max(4, Math.round((target / max) * 100));
    const mineWidth = Math.max(4, Math.round((mine / max) * 100));
    const row = document.createElement("div");
    row.className = "visual-row";
    row.innerHTML = `
      <div class="visual-title">
        <strong>${metricNames[key] || key}</strong>
        <span>${metric.delta > 0 ? "目标领先" : metric.delta < 0 ? "我方领先" : "持平"}</span>
      </div>
      <div class="bar-pair">
        <span>目标</span>
        <div class="bar-shell"><div class="bar target" style="width:${targetWidth}%"></div></div>
        <b>${valueText(key, target)}</b>
      </div>
      <div class="bar-pair">
        <span>我</span>
        <div class="bar-shell"><div class="bar mine" style="width:${mineWidth}%"></div></div>
        <b>${valueText(key, mine)}</b>
      </div>
    `;
    host.appendChild(row);
  }
}

function renderAi(ai) {
  const panel = document.querySelector("#aiPanel");
  const message = document.querySelector("#aiMessage");
  panel.classList.remove("hidden");
  document.querySelector("#aiModelText").textContent = ai.enabled ? ai.model || "AI 已启用" : "规则分析";
  addList("#aiInsights", ai.insights || []);
  addList("#aiActions", ai.action_plan || []);
  addList("#aiExperiments", ai.content_experiments || []);
  message.textContent = ai.message || "";
}

function renderResults(data) {
  results.classList.remove("hidden");

  const summaryBand = document.querySelector("#summaryBand");
  summaryBand.innerHTML = "";
  for (const text of data.summary || []) {
    const p = document.createElement("p");
    p.textContent = text;
    summaryBand.appendChild(p);
  }

  renderCompareHero(data);
  renderVisualMetrics(data);
  renderAi(data.ai_analysis || {});

  addList("#targetAdvantages", data.comparison.target_advantages);
  addList("#lessons", data.comparison.lessons);

  const topicDiff = document.querySelector("#topicDiff");
  topicDiff.innerHTML = "";
  for (const topic of data.comparison.shared_topics || []) {
    topicDiff.appendChild(tag(`共同主题：${topic}`, "blue"));
  }
  for (const topic of data.comparison.target_unique_topics || []) {
    topicDiff.appendChild(tag(`目标突出：${topic}`, "coral"));
  }
  for (const keyword of data.comparison.target_unique_keywords || []) {
    topicDiff.appendChild(tag(`表达借鉴：${keyword}`, ""));
  }

  const topNotes = document.querySelector("#topNotes");
  topNotes.innerHTML = "";
  for (const note of data.target.top_notes || []) {
    const item = document.createElement("div");
    item.className = "note-item";
    const title = note.note_url
      ? `<a class="note-title" href="${note.note_url}" target="_blank" rel="noreferrer">${escapeHtml(note.title)}</a>`
      : `<div class="note-title">${escapeHtml(note.title)}</div>`;
    item.innerHTML = `
      ${title}
      <div class="note-meta">
        <span>赞 ${note.liked_count}</span>
        <span>藏 ${note.collected_count}</span>
        <span>评 ${note.comment_count}</span>
        <span>分享 ${note.share_count}</span>
      </div>
    `;
    topNotes.appendChild(item);
  }

  loadHistory();
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function tag(text, tone) {
  const span = document.createElement("span");
  span.className = `tag ${tone}`;
  span.textContent = text;
  return span;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

let currentPollId = 0;

async function pollTask(taskId) {
  const pollId = ++currentPollId;
  while (pollId === currentPollId) {
    try {
      const response = await fetch(`/api/tasks/${taskId}`);
      if (!response.ok) {
        stageText.textContent = "任务查询失败";
        renderLogs(["任务不存在或已过期，请重新提交。"]);
        submitButton.disabled = false;
        submitButton.textContent = "重新分析";
        hideQrcode();
        return;
      }
      const task = await response.json();
      stageText.textContent = task.stage;
      progressBar.style.width = `${task.progress}%`;
      renderLogs(task.logs || []);

      // Check if QR code login is needed
      const logs = task.logs || [];
      const loginSuccess = logs.some(
        (l) => l.includes("扫码登录成功") || l.includes("Login successful") || l.includes("Login state result: True")
      );
      if (loginSuccess) {
        hideQrcode();
      } else {
        const needsSms = logs.some(
          (l) => l.includes("需要短信验证码") || l.includes("安全验证")
        );
        const needsQrcode = logs.some(
          (l) => l.includes("扫码") || l.includes("qrcode") || l.includes("waiting for scan")
        );
        if (needsSms && task.status === "running") {
          tryFetchQrcode(taskId);
          showSmsInput(taskId);
        } else if (needsQrcode && task.status === "running") {
          tryFetchQrcode(taskId);
        } else {
          hideQrcode();
        }
      }

      if (task.status === "completed") {
        submitButton.disabled = false;
        submitButton.textContent = "重新分析";
        hideQrcode();
        renderResults(task.result);
        return;
      }

      if (task.status === "failed") {
        submitButton.disabled = false;
        submitButton.textContent = "重新分析";
        stageText.textContent = "失败";
        hideQrcode();
        renderLogs([...(task.logs || []), task.error || "任务失败"]);
        return;
      }
    } catch {
      // network hiccup — keep polling
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

async function tryFetchQrcode(taskId) {
  try {
    const resp = await fetch(`/api/qrcode/${taskId}?t=${Date.now()}`);
    if (resp.ok) {
      const blob = await resp.blob();
      qrcodeImage.src = URL.createObjectURL(blob);
      qrcodeOverlay.classList.remove("hidden");
    }
  } catch {
    // not ready yet
  }
}

function hideQrcode() {
  qrcodeOverlay.classList.add("hidden");
  smsCodeSection.classList.add("hidden");
  if (qrcodeImage.src) {
    URL.revokeObjectURL(qrcodeImage.src);
    qrcodeImage.src = "";
  }
}

function showSmsInput(taskId) {
  qrcodeTitle.textContent = "需要安全验证";
  qrcodeHint.textContent = "";
  smsCodeSection.classList.remove("hidden");
  smsCodeInput.focus();
  smsCodeSubmit.onclick = async () => {
    const code = smsCodeInput.value.trim();
    if (!code) return;
    smsCodeSubmit.disabled = true;
    smsCodeSubmit.textContent = "提交中...";
    try {
      await fetch(`/api/sms_code/${taskId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      smsCodeSection.classList.add("hidden");
      qrcodeTitle.textContent = "验证码已提交，等待验证...";
    } catch {
      smsCodeSubmit.disabled = false;
      smsCodeSubmit.textContent = "重新提交";
    }
  };
}

async function loadHistory() {
  try {
    const response = await fetch("/api/history");
    const items = await response.json();
    historyList.innerHTML = "";
    if (!items.length) {
      historyList.innerHTML = '<p class="hint">暂无历史记录。</p>';
      return;
    }
    for (const item of items.slice(0, 8)) {
      const button = document.createElement("button");
      button.className = "history-item";
      button.type = "button";
      button.innerHTML = `
        <strong>${escapeHtml(item.my_name)} vs ${escapeHtml(item.target_name)}</strong>
        <span>${item.created_at}</span>
        <em>${escapeHtml((item.summary || [])[0] || "点击查看历史分析")}</em>
      `;
      button.addEventListener("click", async () => {
        const detail = await fetch(`/api/history/${item.id}`).then((res) => res.json());
        renderResults(detail.result);
      });
      historyList.appendChild(button);
    }
  } catch (error) {
    historyList.innerHTML = '<p class="hint">历史记录读取失败。</p>';
  }
}

document.querySelector("#refreshHistory").addEventListener("click", loadHistory);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  currentPollId++; // cancel any running poll loop
  hideQrcode();
  results.classList.add("hidden");
  submitButton.disabled = true;
  submitButton.textContent = "分析中";
  stageText.textContent = "提交任务";
  progressBar.style.width = "3%";
  renderLogs(["任务已提交，正在准备。"]);

  const payload = {
    my_homepage: document.querySelector("#myHomepage").value.trim(),
    target_homepage: document.querySelector("#targetHomepage").value.trim(),
    max_notes: Number(document.querySelector("#maxNotes").value || 30),
    max_comments_per_note: Number(document.querySelector("#maxComments").value || 20),
    include_comments: document.querySelector("#includeComments").checked,
    enable_ai_analysis: document.querySelector("#enableAi").checked,
    headless: true,
    reuse_existing_data: document.querySelector("#reuseData").checked,
  };

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("提交失败");
    const created = await response.json();
    await pollTask(created.task_id);
  } catch (error) {
    submitButton.disabled = false;
    submitButton.textContent = "重新分析";
    stageText.textContent = "提交失败";
    renderLogs([error.message || "提交失败"]);
  }
});

checkHealth();
loadLlmSettings();
loadHistory();
