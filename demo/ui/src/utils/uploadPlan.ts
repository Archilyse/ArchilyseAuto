import { auth, request } from '../providers';
import {
  processedWalls,
  processedIcons,
  processedSpaces,
  processedBackground,
  wallTimer,
  iconTimer,
  spacesTimer,
} from '../stores';
import { get } from 'svelte/store';
import { ENDPOINTS } from '../constants';
import type { RetrieveStatsBody } from '../types';

const UNAUTHENTICATED = 'unauthenticated';
const { RETRIEVE_RESULTS, RETRIEVE_BACKGROUND, UPLOAD_URL } = ENDPOINTS;
// @TODO: Set task status in store accordingly so we can show it later in loading

enum TaskStatus { // https://docs.celeryq.dev/en/stable/reference/celery.result.html#celery.result.AsyncResult.status
  PENDING = 'PENDING',
  STARTED = 'STARTED',
  RETRY = 'RETRY',
  FAILURE = 'FAILURE',
  SUCCESS = 'SUCCESS',
}

type task = {
  id: string;
  status: TaskStatus;
};

// Below constants will make the app poll during 300 sec before giving up
const MAX_POLL_ITERATIONS = 30;
const POLL_INTERVAL_MS = 10 * 1000;

const resultsAreReady = response => response.headers['content-type'] === 'image/svg';

const cancelPolling = timer => {
  console.debug('Clearing poll timer', get(timer));
  clearInterval(get(timer));
  timer.set(null);
};

const fetchData = async (task: task, timer) => {
  // @TODO: Pass the specific store here to set its status
  let response = null;
  let iterations = 0;

  return new Promise((resolve, reject) => {
    const t = setInterval(async () => {
      try {
        if (iterations > MAX_POLL_ITERATIONS) {
          cancelPolling(timer);
          return reject('No response from backend');
        }

        response = await request.get(`${RETRIEVE_RESULTS}/${task.id}`, { responseType: 'blob' });

        if (resultsAreReady(response)) {
          cancelPolling(timer);
          return resolve(response);
        } else {
          const regularResponse = await response.data.text();
          const status = JSON.parse(regularResponse).status;
          console.debug(`Still processing, task status: ${status}`);
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

const fetchWalls = async (wallTask: task) => {
  const response = await fetchData(wallTask, wallTimer);
  const url = URL.createObjectURL(response.data);
  processedWalls.set(url);
};

const fetchIcons = async (iconTask: task) => {
  const response = await fetchData(iconTask, iconTimer);
  const url = URL.createObjectURL(response.data);
  processedIcons.set(url);
};

const fetchSpaces = async (spacesTask: task) => {
  const response = await fetchData(spacesTask, spacesTimer);
  const url = URL.createObjectURL(response.data);
  processedSpaces.set(url);
};

const fetchBackground = async (wallTask: task, iconTask: task, spacesTask: task) => {
  const response = await request.post(
    `${RETRIEVE_BACKGROUND}`,
    { tasks: [wallTask.id, iconTask.id, spacesTask.id] },
    { responseType: 'blob' }
  );
  const url = URL.createObjectURL(response.data);
  processedBackground.set(url);
};

const uploadPlan = async (fileToUpload: File): Promise<RetrieveStatsBody> => {
  cancelPolling(wallTimer);
  cancelPolling(iconTimer);
  cancelPolling(spacesTimer);

  const formData = new FormData();
  formData.append('image', fileToUpload);
  const user = await auth.getUser();

  const response = await request.post(UPLOAD_URL, formData, { headers: { username: user?.email || UNAUTHENTICATED } });
  const { wall_task, icon_task, spaces_task }: { wall_task: task; icon_task: task; spaces_task: task; } = response.data;
  await Promise.all([fetchWalls(wall_task), fetchIcons(icon_task), fetchSpaces(spaces_task)]);
  await fetchBackground(wall_task, icon_task, spaces_task);

  return { walls_task_id: wall_task.id, icons_task_id: icon_task.id, spaces_task_id: spaces_task.id };
};

export default uploadPlan;
