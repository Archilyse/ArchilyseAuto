import axios, { type AxiosRequestConfig } from "axios";
import { getBaseURL } from "../utils";

const instance = axios.create({
    baseURL: getBaseURL(),
});
type AbortControllers = {
    [url: string]: AbortController;
};
const controllers: AbortControllers = {};

async function get(url, options: AxiosRequestConfig = {}) {
    return instance.get(url, options);
}
async function post(url, data, options: AxiosRequestConfig = {}) {
    // Abort any ongoing request with the same url to always show the most recent response in the UI
    if (controllers[url]) controllers[url].abort();

    controllers[url] = new AbortController();
    return instance.post(url, data, {
        signal: controllers[url].signal,
        ...options,
    });
}

async function put(url, data, options: AxiosRequestConfig = {}) {
    return instance.put(url, data, options);
}

export default {
    get,
    post,
    put,
};
