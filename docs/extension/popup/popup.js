document.addEventListener("DOMContentLoaded", () => {

    const currentSite =
        document.getElementById("currentSite");

    const analyzeButton =
        document.getElementById("analyzeButton");

    const statusIcon =
        document.getElementById("statusIcon");

    const statusText =
        document.getElementById("statusText");

    const statusDescription =
        document.getElementById("statusDescription");

    const anomalyScore =
        document.getElementById("anomalyScore");

    const scoreProgress =
        document.getElementById("scoreProgress");

    const detectionStatus =
        document.getElementById("detectionStatus");

    const severity =
        document.getElementById("severity");

    const attackType =
        document.getElementById("attackType");


    /*
     * Get the currently active browser tab.
     */

    chrome.tabs.query(
        {
            active: true,
            currentWindow: true
        },

        (tabs) => {

            if (!tabs || tabs.length === 0) {
                currentSite.textContent =
                    "Unable to detect website";

                return;
            }

            const url = tabs[0].url;

            currentSite.textContent =
                url || "Unknown";
        }
    );


    /*
     * Temporary test analysis.
     *
     * Later this will call our
     * Network Anomaly Detection API.
     */

    analyzeButton.addEventListener(
        "click",
        () => {

            const testResult = {
                prediction: "NORMAL",
                anomaly_score: 0.12,
                severity: "LOW",
                attack_type: "NONE"
            };


            const score =
                Math.round(
                    testResult.anomaly_score * 100
                );


            anomalyScore.textContent =
                `${score}%`;

            scoreProgress.style.width =
                `${score}%`;


            statusIcon.textContent = "✓";

            statusText.textContent =
                "SYSTEM NORMAL";

            statusDescription.textContent =
                "No anomaly detected";


            detectionStatus.textContent =
                "Normal";

            severity.textContent =
                testResult.severity;

            attackType.textContent =
                testResult.attack_type;

        }
    );

}); 