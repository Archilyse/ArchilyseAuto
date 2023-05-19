import { writable } from "svelte/store";
import type { RetrieveStatsResponse } from "./types";

export const authError = writable<Error>(null);
export const processedWalls = writable<string | null>(null);
export const processedIcons = writable<string | null>(null);
export const processedSpaces = writable<string | null>(null);
export const processedBackground = writable<string | null>(null);
export const processedStats = writable<RetrieveStatsResponse | null>(null);

export const wallTimer = writable<any>(null);
export const iconTimer = writable<any>(null);
export const spacesTimer = writable<any>(null);
export const backgroundTimer = writable<any>(null);
export const statisticsTimer = writable<any>(null);
