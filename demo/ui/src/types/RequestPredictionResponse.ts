import type { Task } from "./Task";

export type RequestPredictionResponse = {
    wall_task: Task;
    icon_task: Task;
    spaces_task: Task;
    statistics_task: Task;
    background_task: Task;
};
