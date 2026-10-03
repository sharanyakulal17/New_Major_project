const API = "http://10.148.160.34:5001/api/v1";

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

const responseInput = document.getElementById("responseLoad");
const durationInput = document.getElementById("duration");

const targetResponse = document.getElementById("targetResponse");
const currentResponse = document.getElementById("currentResponse");
const responseStatus = document.getElementById("responseStatus");

const targetInfo = document.getElementById("targetInfo");
const responseInfo = document.getElementById("responseInfo");

const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");

const elapsedTime = document.getElementById("elapsedTime");

let loadRunning = false;
let elapsedTimer = null;
let stopTimer = null;
let startTime = null;


// ===============================
// UPDATE UI
// ===============================

function updateResponseDisplay(value) {

    targetResponse.textContent = `${value} ms`;
    currentResponse.textContent = `${value} ms`;

    targetInfo.textContent = `${value} ms`;
    responseInfo.textContent = `${value} ms`;
}


// ===============================
// SEND RESPONSE LOAD TO BACKEND
// ===============================

async function sendResponseLoad(value) {

    const response = await fetch(`${API}/response-load`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            response_time: value
        })

    });

    if (!response.ok) {
        throw new Error("Failed to update response load.");
    }

    return await response.json();
}


// ===============================
// START LOAD
// ===============================

startBtn.addEventListener("click", async function () {

    const responseLoad = Number(responseInput.value);
    const duration = Number(durationInput.value);

    if (
        !Number.isFinite(responseLoad) ||
        responseLoad < 100 ||
        responseLoad > 5000
    ) {

        alert("Response time must be between 100 ms and 5000 ms.");

        return;
    }


    if (
        !Number.isFinite(duration) ||
        duration < 1
    ) {

        alert("Duration must be at least 1 second.");

        return;
    }


    try {

        // Send load to backend
        await sendResponseLoad(responseLoad);


        // Update state
        loadRunning = true;

        startBtn.disabled = true;
        stopBtn.disabled = false;


        // Update UI
        statusText.textContent = "Running";
        responseStatus.textContent = "Running";

        updateResponseDisplay(responseLoad);


        // Reset elapsed time
        startTime = Date.now();

        elapsedTime.textContent = "0 sec";


        // Clear old timers
        clearInterval(elapsedTimer);
        clearTimeout(stopTimer);


        // Elapsed time counter
        elapsedTimer = setInterval(function () {

            const elapsed =
                Math.floor(
                    (Date.now() - startTime) / 1000
                );

            elapsedTime.textContent =
                `${elapsed} sec`;

        }, 1000);


        // Automatically stop after duration
        stopTimer = setTimeout(function () {

            stopResponseLoad();

        }, duration * 1000);


        console.log(
            "Response time load started:",
            responseLoad,
            "ms"
        );

    }

    catch (error) {

        console.error(error);

        alert(
            "Could not start response-time load. " +
            "Make sure the backend is running."
        );

    }

});


// ===============================
// STOP LOAD
// ===============================

stopBtn.addEventListener("click", function () {

    stopResponseLoad();

});


// ===============================
// STOP RESPONSE LOAD FUNCTION
// ===============================

async function stopResponseLoad() {

    if (!loadRunning) {
        return;
    }


    // Stop timers
    clearInterval(elapsedTimer);
    clearTimeout(stopTimer);


    try {

        // Return response time to healthy value
        await sendResponseLoad(100);

    }

    catch (error) {

        console.error(
            "Failed to reset response load:",
            error
        );

    }


    // Update state
    loadRunning = false;


    // Update buttons
    startBtn.disabled = false;
    stopBtn.disabled = true;


    // Update status
    statusText.textContent = "Idle";
    responseStatus.textContent = "Idle";


    // Reset display
    updateResponseDisplay(100);

    elapsedTime.textContent = "0 sec";


    console.log(
        "Response time load stopped."
    );

}