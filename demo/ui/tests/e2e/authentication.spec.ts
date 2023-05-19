import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';
import login from './utils/login.js';
import uploadFile from './utils/uploadFile.js';
import loginInPopup from './utils/loginInPopup.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SAMPLE_PLAN = path.resolve(__dirname, '../fixtures/sample_plan.jpg');


test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test.describe('Authenticate in the web app', () => {
  
  test('Unauthenticated users trying to upload a file will get a popup to authenticate before continuing', async ({ browser, browserName }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.goto('/');

    // Trying to upload
    await page.getByText(/Drop a plan here or click to upload/).click();
    await uploadFile(page, browserName, SAMPLE_PLAN);

    // Should show a popup
    await expect(page.getByText(/Create an account to upload plans/)).toBeVisible();
    // If we authenticate
    await loginInPopup(page, context);
    // The upload continues
    await expect(page.getByText(/Loading.../)).toBeVisible();
  });

  test('Authenticated users can upload files without a popup', async ({ page,browserName }) => {
    await login(page);
    await uploadFile(page, browserName, SAMPLE_PLAN);
    await expect(page.getByText(/Create an account to upload plans/)).not.toBeVisible();

    // Ensure no query params after authentication
    await expect(async () => {
      const queryParams = page.url().split('?')[1]
      await expect(queryParams).toBeUndefined();
    }).toPass();
  });

  test('Unauthenticated users can still drag and drop preloaded plans into the file-dropzone', async ({ page }) => {
    // Find a preloaded plan to be dragged
    const planToDrag = await page.getByAltText('Thumbnail of plan').first();
  
    // Trigger a drag event on a preloaded plan
    await planToDrag.dispatchEvent('dragend');
  
    // The upload starts
    await expect(page.getByText(/Loading.../)).toBeVisible();
  });


});
