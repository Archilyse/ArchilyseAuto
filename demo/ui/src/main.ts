import "./global.css";
import App from "./components/App.svelte";
import * as Sentry from "@sentry/svelte";
import { CaptureConsole } from "@sentry/integrations";

const app = new App({
    target: document.body,
});

const isProd = import.meta.env.PROD && window.location.protocol === "https:";

Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    enabled: isProd,
    environment: "demo-ui",
    integrations: [
        new CaptureConsole({
            levels: ["error"],
        }) as CaptureConsole,
    ],
});

export default app;
