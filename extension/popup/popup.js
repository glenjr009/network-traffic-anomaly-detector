
document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

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

  const STALE_AFTER_MS = 60_000;

  let latestResult = null;
  let freshnessTimer = null;

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

      // Browser internal pages are not ordinary websites.
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

    // Only display fields actually provided by the backend.
    severity.textContent = result.severity || "Not provided";
    attackType.textContent = result.attack_type || "Not provided";
    modelName.textContent = result.model || "Not provided";

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

  function loadStoredDetection() {
    chrome.storage.local.get(["latestDetection"], (data) => {
      if (chrome.runtime.lastError) {
        console.error(
          "Could not read stored detection:",
          chrome.runtime.lastError.message
        );
        resetDisplay();
        statusDescription.textContent =
          "Could not read the latest stored result.";
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
    chrome.tabs.query(
      { active: true, currentWindow: true },
      (tabs) => {
        if (chrome.runtime.lastError) {
          currentSite.textContent = "Tab information unavailable";
          return;
        }

        currentSite.textContent = formatSite(tabs?.[0]?.url);
      }
    );
  }

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (
      areaName === "local" &&
      changes.latestDetection
    ) {
      displayDetection(changes.latestDetection.newValue);
    }
  });

  loadCurrentTab();
  loadStoredDetection();

  freshnessTimer = window.setInterval(updateFreshness, 5_000);

  window.addEventListener("unload", () => {
    if (freshnessTimer !== null) {
      window.clearInterval(freshnessTimer);
    }
  });
});
