import { accessSync } from 'fs';
import { devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import path from 'path';
import type { PlaywrightTestConfig } from '@playwright/test';


function loadEnvFile() {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  let envFile = path.resolve(__dirname, '.env');
  accessSync(envFile);
  dotenv.config({ path: envFile });
}


loadEnvFile();

/** IMPORTANT: Tests requires node 16.18.0+ to work */

/**
 * See https://playwright.dev/docs/test-configuration.
 */
const config: PlaywrightTestConfig = {
  testDir: './tests',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  /* Run tests in files in parallel */
  // fullyParallel: false, //@TODO: To be adjusted: Local API might be too slow with many parallel requests.
  workers: 2, //@TODO: To be adjusted: Local API might be too slow with many parallel requests.
  reporter: 'list',
  use: {
    /* Maximum time each action such as `click()` can take. Defaults to 0 (no limit). */
    actionTimeout: 0,
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost',
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    //
    // {
    //   name: 'firefox',
    //   use: {
    //     ...devices['Desktop Firefox'],
    //   },
    // },
    //
    // {
    //   name: 'webkit',
    //   use: {
    //     ...devices['Desktop Safari'],
    //   },
    // },

    /* Test against mobile viewports. */
    // {
    //   name: 'Mobile Chrome',
    //   use: {
    //     ...devices['Pixel 5'],
    //   },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: {
    //     ...devices['iPhone 12'],
    //   },
    // },

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: {
    //     channel: 'msedge',
    //   },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: {
    //     channel: 'chrome',
    //   },
    // },
  ],
};

export default config;
