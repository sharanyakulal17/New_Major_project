let isRunning = false;
let startTime = 0;
let timerInterval = null;

// ================= ELEMENTS =================

const targetUrl = document.getElementById("targetUrl");
const trafficLoad = document.getElementById("trafficLoad");
const duration = document.getElementById("duration");

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const requestsSentElement = document.getElementById("requestsSent");
const successfulRequestsElement = document.getElementById("successfulRequests");
const failedRequestsElement = document.getElementById("failedRequests");
const responseTimeElement = document.getElementById("responseTime");

const currentLoadElement = document.getElementById("currentLoad");
const totalRequestsElement = document.getElementById("totalRequests");
const elapsedTimeElement = document.getElementById("elapsedTime");

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");


// ================= START LOAD =================

async function startLoad() {

    if (isRunning) {
        return;
    }

    const traffic = Number(trafficLoad.value);
    const loadDuration = Number(duration.value);

    if (!Number.isFinite(traffic) || traffic < 0) {
        alert("Please enter a valid traffic value.");
        return;
    }

    if (!Number.isFinite(loadDuration) || loadDuration < 1) {
        alert("Please enter a valid duration.");
        return;
    }

    const backendUrl =
        targetUrl.value.replace(/\/$/, "") +
        "/api/v1/traffic";

    console.log("SENDING CPU LOAD:", traffic);
    console.log("BACKEND URL:", backendUrl);

    try {

        const requestStart = performance.now();

        const response = await fetch(backendUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                traffic: traffic
            })
        });

        const requestEnd = performance.now();

        responseTimeElement.textContent =
            Math.round(requestEnd - requestStart) + " ms";

        if (!response.ok) {
            const errorText = await response.text();

            throw new Error(
                "Backend returned " +
                response.status +
                ": " +
                errorText
            );
        }

        const data = await response.json();

        console.log("CPU LOAD RESPONSE:", data);

        // ================= RUNNING =================

        isRunning = true;

        startBtn.disabled = true;
        stopBtn.disabled = false;

        statusText.textContent = "Running";
        statusDot.style.background = "#22c55e";

        currentLoadElement.textContent =
            traffic + " req/min";

        requestsSentElement.textContent = traffic;
        successfulRequestsElement.textContent = traffic;
        failedRequestsElement.textContent = "0";
        totalRequestsElement.textContent = traffic;

        startTime = Date.now();

        // ================= TIMER =================

        timerInterval = setInterval(() => {

            const elapsed =
                Math.floor(
                    (Date.now() - startTime) / 1000
                );

            elapsedTimeElement.textContent =
                elapsed + " sec";

            if (elapsed >= loadDuration) {
                stopLoad();
            }

        }, 1000);

    } catch (error) {

        console.error("CPU LOAD ERROR:", error);

        alert(
            "CPU load could not be started.\n\n" +
            error.message
        );
    }
}


// ================= STOP LOAD =================

async function stopLoad() {

    if (!isRunning) {
        return;
    }

    const backendUrl =
        targetUrl.value.replace(/\/$/, "") +
        "/api/v1/traffic";

    try {

        const response = await fetch(backendUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                traffic: 0
            })
        });

        if (!response.ok) {
            console.error(
                "STOP LOAD FAILED:",
                response.status
            );
        }

    } catch (error) {

        console.error(
            "STOP LOAD ERROR:",
            error
        );
    }

    isRunning = false;

    clearInterval(timerInterval);
    timerInterval = null;

    startBtn.disabled = false;
    stopBtn.disabled = true;

    statusText.textContent = "Stopped";
    statusDot.style.background = "#64748b";

    currentLoadElement.textContent = "0 req/min";
}


// ================= BUTTON EVENTS =================

startBtn.addEventListener(
    "click",
    startLoad
);

stopBtn.addEventListener(
    "click",
    stopLoad
);