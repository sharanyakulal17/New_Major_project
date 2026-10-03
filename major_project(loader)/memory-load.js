const BACKEND = "http://127.0.0.1:5001/api/v1";

let memoryLoadRunning = false;
let memoryTimer = null;
let elapsedSeconds = 0;

const startBtn = document.querySelector("#startBtn");
const stopBtn = document.querySelector("#stopBtn");
const memoryLoadInput = document.getElementById("memoryLoad");
const durationInput = document.getElementById("duration");

const targetMemory = document.getElementById("targetMemory");
const currentMemory = document.getElementById("currentMemory");
const memoryStatus = document.getElementById("memoryStatus");
const elapsedTime = document.getElementById("elapsedTime");

const targetInfo = document.getElementById("targetInfo");
const memoryInfo = document.getElementById("memoryInfo");

async function startMemoryLoad() {
    console.log("START BUTTON WORKS");

    const target = Number(memoryLoadInput.value || 90);
    const duration = Number(durationInput.value || 30);

    if (target < 1 || target > 95) {
        alert("Memory load must be between 1% and 95%.");
        return;
    }

    memoryLoadRunning = true;
    elapsedSeconds = 0;

    startBtn.disabled = true;
    stopBtn.disabled = false;

    targetMemory.textContent = target + "%";
    targetInfo.textContent = target + "%";

    memoryStatus.textContent = "Running";

    await sendMemoryLoad(target);

    memoryTimer = setInterval(async () => {
    if (!memoryLoadRunning) return;

    elapsedSeconds++;
    elapsedTime.textContent = elapsedSeconds + " sec";

    try {
        const response = await fetch(
            BACKEND + "/load/memory"
        );

        const data = await response.json();

        if (data.memory !== undefined) {

            const value =
                Number(data.memory).toFixed(1) + "%";

            currentMemory.textContent = value;
            memoryInfo.textContent = value;

            // Recovery has lowered the memory
            if (Number(data.memory) < 90) {

                memoryStatus.textContent =
                    "Recovered";

                stopMemoryLoad();

                return;
            }
        }

    } catch (error) {

        console.error(
            "MEMORY STATUS ERROR:",
            error
        );
    }

    if (elapsedSeconds >= duration) {
        stopMemoryLoad();
    }

}, 1000);

}

async function sendMemoryLoad(target) {

    try {

        const response = await fetch(
            BACKEND + "/load/memory",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    memory: target
                })
            }
        );

        if (!response.ok) {
            throw new Error(
                "Memory load request failed: " +
                response.status
            );
        }

        const data = await response.json();

        console.log("MEMORY LOAD:", data);

        if (data.memory !== undefined) {

            const value =
                Number(data.memory).toFixed(1) + "%";

            currentMemory.textContent = value;
            memoryInfo.textContent = value;
        }

    }
    catch (error) {

        console.error(
            "MEMORY LOAD ERROR:",
            error
        );

        memoryStatus.textContent = "Backend Error";
    }
}

function stopMemoryLoad() {

    memoryLoadRunning = false;

    if (memoryTimer) {
        clearInterval(memoryTimer);
        memoryTimer = null;
    }

    startBtn.disabled = false;
    stopBtn.disabled = true;

    memoryStatus.textContent = "Stopped";

    }

    startBtn.addEventListener(
    "click",
    startMemoryLoad
    );

    stopBtn.addEventListener(
    "click",
    stopMemoryLoad
    );
