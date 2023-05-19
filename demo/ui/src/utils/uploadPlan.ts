import { auth, request } from "../providers";
import {
    processedWalls,
    processedIcons,
    processedSpaces,
    processedBackground,
    processedStats,
    wallTimer,
    iconTimer,
    spacesTimer,
    backgroundTimer,
    statisticsTimer,
} from "../stores";
import { get } from "svelte/store";
import { ENDPOINTS, UPLOAD_CONFIG, UNAUTHENTICATED } from "../constants";
import type { RequestPredictionResponse, RetrieveStatsResponse, Task } from "../types";
import type { AxiosResponse } from "axios";

// Below constants will make the app poll during 300 sec before giving up
// @TODO: Stores here are probably not the most performant thing https://svelte.dev/docs#run-time-svelte-store-get
const MAX_POLL_ITERATIONS = 30;
const POLL_INTERVAL_MS = 10 * 1000;

const resultsAreReady = (response) => response.status === 200;

const cancelPolling = (timer) => {
    console.debug("Clearing poll timer", get(timer));
    clearInterval(get(timer));
    timer.set(null);
};

const fetchData = async (url, timer): Promise<AxiosResponse> => {
    // @TODO: Pass the specific store here to set its status
    let response = null;
    let iterations = 0;

    return new Promise((resolve, reject) => {
        const t = setInterval(async () => {
            try {
                if (iterations > MAX_POLL_ITERATIONS) {
                    cancelPolling(timer);
                    return reject("Max poll iterations reached, API did not respond with results");
                }

                response = await request.get(url);

                if (resultsAreReady(response)) {
                    cancelPolling(timer);
                    return resolve(response);
                } else {
                    console.debug(`Still processing ...`);
                }

                iterations++;
            } catch (error) {
                cancelPolling(timer);
                return reject(error);
            }
        }, POLL_INTERVAL_MS);
        timer.set(t);
    });
};

const uploadImage = async (user, image) => {
    const headers = {
        username: user?.email || UNAUTHENTICATED,
    };

    const isAuthenticated = await auth.isAuthenticated();
    if (isAuthenticated) {
        const accessToken = await auth.getAuthToken();
        headers["Authorization"] = `Bearer ${accessToken};`;
    }

    const response = await request.get(`${ENDPOINTS.UPLOAD_URL}?content_type=${image.type}`, { headers });
    await request.put(response.data.url, image, {
        headers: {
            "x-goog-content-length-range": `0,${UPLOAD_CONFIG.MAX_FILE_SIZE}`,
            "Content-Type": image.type,
        },
    });
    return response.data.image_name;
};

const requestPrediction = async (imageName: string): Promise<RequestPredictionResponse> => {
    const response: { data: RequestPredictionResponse } = await request.post(
        `${ENDPOINTS.REQUEST_PREDICTION}?image_name=${imageName}`,
        {}
    );
    return response.data;
};

const fetchWalls = async (wallTask: Task) => {
    const response = await fetchData(`${ENDPOINTS.RETRIEVE_RESULTS}/${wallTask.id}.svg`, wallTimer);
    const blob = new Blob([response.data], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    processedWalls.set(url);
};

const fetchIcons = async (iconTask: Task) => {
    const response = await fetchData(`${ENDPOINTS.RETRIEVE_RESULTS}/${iconTask.id}.svg`, iconTimer);
    const blob = new Blob([response.data], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    processedIcons.set(url);
};

const fetchSpaces = async (spacesTask: Task) => {
    const response = await fetchData(`${ENDPOINTS.RETRIEVE_RESULTS}/${spacesTask.id}.svg`, spacesTimer);
    const blob = new Blob([response.data], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    processedSpaces.set(url);
};

const fetchBackground = async (backgroundTask: Task) => {
    const response = await fetchData(`${ENDPOINTS.RETRIEVE_RESULTS}/${backgroundTask.id}.svg`, backgroundTimer);
    const blob = new Blob([response.data], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    processedBackground.set(url);
};

const fetchStats = async (statisticsTask: Task) => {
    const response: { data: RetrieveStatsResponse } = await fetchData(
        `${ENDPOINTS.RETRIEVE_RESULTS}/${statisticsTask.id}.json`,
        statisticsTimer
    );
    processedStats.set(response.data);
};

const fetchResults = async (tasks: RequestPredictionResponse) => {
    const { wall_task, icon_task, spaces_task, statistics_task, background_task } = tasks;
    await Promise.all([fetchWalls(wall_task), fetchIcons(icon_task), fetchSpaces(spaces_task)]);
    await Promise.all([fetchBackground(background_task), fetchStats(statistics_task)]);
};

const uploadPlan = async (fileToUpload: File) => {
    cancelPolling(wallTimer);
    cancelPolling(iconTimer);
    cancelPolling(spacesTimer);
    cancelPolling(backgroundTimer);
    cancelPolling(statisticsTimer);

    const user = await auth.getUser();
    const imageName: string = await uploadImage(user, fileToUpload);
    const tasks = await requestPrediction(imageName);
    await fetchResults(tasks);
};

export default uploadPlan;
