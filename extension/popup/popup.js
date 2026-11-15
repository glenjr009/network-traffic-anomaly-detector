document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

  // Monitor elements
  const heroCard = $("heroCard");
  const statusIcon = $("statusIcon");
  const statusText = $("statusText");
  const statusDescription = $("statusDescription");
  const statusPillText = $("statusPillText");
  const lastSeen = $("lastSeen");

  const confidenceValue = $("confidenceValue");
  const confidenceMeter = $("confidenceMeter");
  const scoreProgress = $("scoreProgress");
  const confidenceHint = $("confidenceHint");

  const detectionStatus = $("detectionStatus");
  const severity = $("severity");
  const attackType = $("attackType");
  const modelName = $("modelName");
  const currentSite = $("currentSite");
  const explainAlertBtn = $("explainAlertBtn");

  // Tab elements
  const tabMonitorBtn = $("tabMonitorBtn");
  const tabChatBtn = $("tabChatBtn");
  const monitorView = $("monitorView");
  const chatView = $("chatView");

  // Chat elements
  const chatMessages = $("chatMessages");
  const chatForm = $("chatForm");
  const chatInput = $("chatInput");
  const chatSendBtn = $("chatSendBtn");
  const ragStatusBadge = $("ragStatusBadge");

  const API_BASE = "http://127.0.0.1:8000";
  const STALE_AFTER_MS = 60_000;

  let latestResult = null;
  let freshnessTimer = null;

  // ============================================================
  // TAB NAVIGATION
  // ============================================================

  function switchTab(target) {
    if (target === "chat") {
      tabChatBtn.classList.add("active");
      tabMonitorBtn.classList.remove("active");
      chatView.classList.add("active");
      monitorView.classList.remove("active");
      chatInput.focus();
    } else {
      tabMonitorBtn.classList.add("active");
      tabChatBtn.classList.remove("active");
      monitorView.classList.add("active");
      chatView.classList.remove("active");
    }
  }

  tabMonitorBtn.addEventListener("click", () => switchTab("monitor"));
  tabChatBtn.addEventListener("click", () => switchTab("chat"));

  // Quick chip queries
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const query = chip.getAttribute("data-query");
      if (query) {
        chatInput.value = query;
        sendMessage(query);
      }
    });
  });

  // Explain Alert Button
  explainAlertBtn.addEventListener("click", () => {
    if (!latestResult) return;
    switchTab("chat");
    explainDetection(latestResult);
  });

  // ============================================================
  // TIME & SITE FORMATTING
  // ============================================================

  function formatAge(timestamp) {
    const time = Date.parse(timestamp);

    if (!Number.isFinite(time)) {
      return "Time unavailable";
    }

    const age = Date.now() - time;

    if (age < -60_000) {
      return "Clock mismatch";
    }

    if (age < 5_000) {
      return "Just now";
    }

    if (age < 60_000) {
      return `${Math.floor(age / 1000)}s ago`;
    }

    if (age < 3_600_000) {
      return `${Math.floor(age / 60_000)}m ago`;
    }

    return `${Math.floor(age / 3_600_000)}h ago`;
  }

  function formatSite(url) {
    if (!url) {
      return "No active tab detected";
    }

    try {
      const parsed = new URL(url);

      if (["chrome:", "edge:", "about:"].includes(parsed.protocol)) {
        return "Browser internal page";
      }

      return parsed.hostname || "Unknown website";
    } catch {
      return "Website unavailable";
    }
  }

  function setState(state) {
    heroCard.classList.remove(
      "state-normal",
      "state-attack",
      "state-stale"
    );

    if (state) {
      heroCard.classList.add(`state-${state}`);
    }
  }

  function resetDisplay() {
    latestResult = null;
    setState(null);

    statusIcon.textContent = "—";
    statusText.textContent = "Waiting for detection";
    statusDescription.textContent =
      "No model result has been received yet.";
    statusPillText.textContent = "WAITING";
    lastSeen.textContent = "No results received";

    confidenceValue.textContent = "—";
    scoreProgress.style.width = "0%";
    confidenceMeter.setAttribute("aria-valuenow", "0");
    confidenceHint.textContent =
      "Confidence will appear when a model result arrives.";

    detectionStatus.textContent = "—";
    severity.textContent = "—";
    attackType.textContent = "—";
    modelName.textContent = "—";

    explainAlertBtn.style.display = "none";
  }

  function displayDetection(result) {
    if (
      !result ||
      !["NORMAL", "ANOMALY"].includes(result.prediction)
    ) {
      resetDisplay();
      return;
    }

    latestResult = result;

    const isAttack = result.prediction === "ANOMALY";
    const confidence = Number(result.confidence);
    const validConfidence =
      Number.isFinite(confidence) &&
      confidence >= 0 &&
      confidence <= 1;

    setState(isAttack ? "attack" : "normal");

    statusIcon.textContent = isAttack ? "!" : "✓";
    statusText.textContent = isAttack
      ? "Anomaly detected"
      : "Traffic classified as normal";

    statusDescription.textContent = isAttack
      ? "The model classified this flow as an attack."
      : "The model classified this flow as benign.";

    statusPillText.textContent = isAttack ? "ATTACK" : "NORMAL";

    if (validConfidence) {
      const percent = Math.round(confidence * 100);

      confidenceValue.textContent = `${percent}%`;
      scoreProgress.style.width = `${percent}%`;
      confidenceMeter.setAttribute(
        "aria-valuenow",
        String(percent)
      );

      confidenceHint.textContent =
        "Confidence in the predicted class; not an anomaly score.";
    } else {
      confidenceValue.textContent = "—";
      scoreProgress.style.width = "0%";
      confidenceMeter.setAttribute("aria-valuenow", "0");
      confidenceHint.textContent =
        "The received result did not contain a valid confidence value.";
    }

    detectionStatus.textContent = isAttack ? "Attack" : "Benign";

    severity.textContent = result.severity || "Not provided";
    attackType.textContent = result.attack_type || "Not provided";
    modelName.textContent = result.model || "Not provided";

    // Show explain button if anomaly detected
    if (isAttack) {
      explainAlertBtn.style.display = "block";
    } else {
      explainAlertBtn.style.display = "none";
    }

    updateFreshness();
  }

  function updateFreshness() {
    if (!latestResult) {
      return;
    }

    const timestamp = latestResult.timestamp;
    lastSeen.textContent = formatAge(timestamp);

    const parsedTime = Date.parse(timestamp);
    const isOld =
      !Number.isFinite(parsedTime) ||
      Date.now() - parsedTime > STALE_AFTER_MS;

    if (isOld) {
      heroCard.classList.add("state-stale");
      statusPillText.textContent = "STALE";
      statusDescription.textContent =
        "This is an older result; waiting for a newer detection.";
    } else {
      heroCard.classList.remove("state-stale");
      statusPillText.textContent =
        latestResult.prediction === "ANOMALY" ? "ATTACK" : "NORMAL";

      statusDescription.textContent =
        latestResult.prediction === "ANOMALY"
          ? "The model classified this flow as an attack."
          : "The model classified this flow as benign.";
    }
  }

  // ============================================================
  // CHATBOT INTERACTION
  // ============================================================

  function appendMessage(sender, text, meta = "") {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble bubble-${sender}`;

    const formattedText = text
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br>");
    bubble.innerHTML = `<p>${formattedText}</p>`;

    if (meta) {
      const metaDiv = document.createElement("div");
      metaDiv.className = "chat-meta";
      metaDiv.innerHTML = meta;
      bubble.appendChild(metaDiv);
    }

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  async function checkRAGStatus() {
    try {
      const res = await fetch(`${API_BASE}/api/rag/status`);
      if (res.ok) {
        const data = await res.json();
        ragStatusBadge.textContent = `${data.chunks_indexed} Chunks · ${data.llm_provider.toUpperCase()}`;
        ragStatusBadge.style.color = "var(--green)";
      }
    } catch {
      ragStatusBadge.textContent = "Offline Mode";
      ragStatusBadge.style.color = "var(--amber)";
    }
  }

  async function sendMessage(query) {
    if (!query || !query.trim()) return;

    appendMessage("user", query);
    chatInput.value = "";
    chatSendBtn.disabled = true;

    const loadingBubble = appendMessage("assistant", "Analyzing threat knowledge base…");

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      loadingBubble.remove();

      let meta = `Mode: ${data.mode} · Latency: ${data.latency_ms}ms`;
      if (data.sources && data.sources.length > 0) {
        const docNames = [...new Set(data.sources.map((s) => s.document_name).filter(Boolean))];
        if (docNames.length > 0) {
          meta += `<br>Sources: ${docNames.join(", ")}`;
        }
      }

      appendMessage("assistant", data.answer, meta);
    } catch (err) {
      loadingBubble.remove();
      appendMessage(
        "assistant",
        `Could not reach NetGuard AI backend (${err.message}). Ensure realtime_api is running at ${API_BASE}.`
      );
    } finally {
      chatSendBtn.disabled = false;
    }
  }

  async function explainDetection(detection) {
    appendMessage(
      "user",
      `⚡ Explain Detection: ${detection.prediction} (${detection.attack_type || "Attack"}) with severity ${detection.severity || "HIGH"}`
    );
    const loadingBubble = appendMessage("assistant", "Cross-referencing telemetry with SOC playbooks…");

    try {
      const res = await fetch(`${API_BASE}/api/chat/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          detection: detection,
          question: "Explain this detected network anomaly, its potential impact, and SOC mitigation actions.",
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      loadingBubble.remove();

      let meta = `Mode: ${data.mode} · Latency: ${data.latency_ms}ms`;
      if (data.sources && data.sources.length > 0) {
        const docNames = [...new Set(data.sources.map((s) => s.document_name).filter(Boolean))];
        if (docNames.length > 0) {
          meta += `<br>Sources: ${docNames.join(", ")}`;
        }
      }

      appendMessage("assistant", data.answer, meta);
    } catch (err) {
      loadingBubble.remove();
      appendMessage("assistant", `Could not generate explanation: ${err.message}`);
    }
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(chatInput.value);
  });

  // ============================================================
  // STORAGE & TAB INITIALIZATION
  // ============================================================

  function loadStoredDetection() {
    if (typeof chrome === "undefined" || !chrome.storage) {
      return;
    }
    chrome.storage.local.get(["latestDetection"], (data) => {
      if (chrome.runtime?.lastError) {
        console.error(
          "Could not read stored detection:",
          chrome.runtime.lastError.message
        );
        resetDisplay();
        return;
      }

      if (data.latestDetection) {
        displayDetection(data.latestDetection);
      } else {
        resetDisplay();
      }
    });
  }

  function loadCurrentTab() {
    if (typeof chrome === "undefined" || !chrome.tabs) {
      currentSite.textContent = "127.0.0.1:8000 (Local)";
      return;
    }
    chrome.tabs.query(
      { active: true, currentWindow: true },
      (tabs) => {
        if (chrome.runtime?.lastError) {
          currentSite.textContent = "Tab information unavailable";
          return;
        }

        currentSite.textContent = formatSite(tabs?.[0]?.url);
      }
    );
  }

  if (typeof chrome !== "undefined" && chrome.storage?.onChanged) {
    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName === "local" && changes.latestDetection) {
        displayDetection(changes.latestDetection.newValue);
      }
    });
  }

  loadCurrentTab();
  loadStoredDetection();
  checkRAGStatus();

  freshnessTimer = window.setInterval(updateFreshness, 5_000);

  window.addEventListener("unload", () => {
    if (freshnessTimer !== null) {
      window.clearInterval(freshnessTimer);
    }
  });
});
