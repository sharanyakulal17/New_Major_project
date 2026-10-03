const BACKEND =
    "http://127.0.0.1:5001/api/v1";

let diskLoadRunning = false;
let diskTimer = null;
let elapsedSeconds = 0;

const startBtn =
    document.getElementById("startBtn");

const stopBtn =
    document.getElementById("stopBtn");

const diskLoadInput =
    document.getElementById("diskLoad");

const durationInput =
    document.getElementById("duration");

const targetDisk =
    document.getElementById("targetDisk");

const currentDisk =
    document.getElementById("currentDisk");

const diskStatus =
    document.getElementById("diskStatus");

const elapsedTime =
    document.getElementById("elapsedTime");

const targetInfo =
    document.getElementById("targetInfo");

const diskInfo =
    document.getElementById("diskInfo");


async function startDiskLoad() {

    console.log(
        "DISK LOAD START BUTTON WORKS"
    );

    const target =
        Number(
            diskLoadInput.value || 90
        );

    const duration =
        Number(
            durationInput.value || 60
        );


    if (
        target < 1 ||
        target > 95
    ) {

        alert(
            "Disk load must be between 1% and 95%."
        );

        return;
    }


    diskLoadRunning = true;

    elapsedSeconds = 0;


    startBtn.disabled = true;

    stopBtn.disabled = false;


    targetDisk.textContent =
        target + "%";

    targetInfo.textContent =
        target + "%";


    diskStatus.textContent =
        "Running";


    await sendDiskLoad(
        target
    );


    diskTimer =
        setInterval(
            async () => {

                if (!diskLoadRunning) {
                    return;
                }


                elapsedSeconds++;

                elapsedTime.textContent =
                    elapsedSeconds +
                    " sec";


                try {

                    const response =
                        await fetch(
                            BACKEND +
                            "/load/disk"
                        );


                    const data =
                        await response.json();


                    console.log(
                        "DISK STATUS:",
                        data
                    );


                    if (
                        data.disk !== undefined
                    ) {

                        const value =
                            Number(
                                data.disk
                            ).toFixed(1) +
                            "%";


                        currentDisk.textContent =
                            value;

                        diskInfo.textContent =
                            value;


                        /*
                         * Recovery has lowered
                         * the simulated disk load.
                         */

                        if (
                            Number(data.disk) < 90
                        ) {

                            diskStatus.textContent =
                                "Recovered";

                            stopDiskLoad();

                            return;
                        }
                    }

                }
                catch (error) {

                    console.error(
                        "DISK STATUS ERROR:",
                        error
                    );

                    diskStatus.textContent =
                        "Backend Error";
                }


                if (
                    elapsedSeconds >=
                    duration
                ) {

                    stopDiskLoad();
                }

            },
            1000
        );
}


async function sendDiskLoad(
    target
) {

    try {

        const response =
            await fetch(
                BACKEND +
                "/load/disk",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            disk: target
                        })
                }
            );


        if (!response.ok) {

            throw new Error(
                "Disk load request failed: " +
                response.status
            );
        }


        const data =
            await response.json();


        console.log(
            "DISK LOAD:",
            data
        );


        if (
            data.disk !== undefined
        ) {

            const value =
                Number(
                    data.disk
                ).toFixed(1) +
                "%";


            currentDisk.textContent =
                value;

            diskInfo.textContent =
                value;
        }

    }
    catch (error) {

        console.error(
            "DISK LOAD ERROR:",
            error
        );

        diskStatus.textContent =
            "Backend Error";
    }
}


function stopDiskLoad() {

    diskLoadRunning = false;


    if (diskTimer) {

        clearInterval(
            diskTimer
        );

        diskTimer = null;
    }


    startBtn.disabled = false;

    stopBtn.disabled = true;


    if (
        diskStatus.textContent !==
        "Recovered"
    ) {

        diskStatus.textContent =
            "Stopped";
    }
}


startBtn.addEventListener(
    "click",
    startDiskLoad
);


stopBtn.addEventListener(
    "click",
    stopDiskLoad
);