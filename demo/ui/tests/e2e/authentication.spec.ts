import { test, expect } from '@playwright/test';
import login from './utils/login.js';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test.describe('Authenticate in the web app', () => {
  test('Unauthenticated users can not upload files', async ({ page }) => {
    await expect(page.getByText(/Drop a plan here or click to upload/)).not.toBeVisible();
    await page.getByText(/Log in with your account to upload plans/).click();
    await expect(page.getByText(/Log in with your account to upload plans/)).toBeVisible();
  });

  test('Unauthenticated users can still drag and drop preloaded plans into the file-dropzone', async ({ page }) => {
    await expect(page.getByText(/Log in with your account to upload plans/)).toBeVisible();

    // Find a preloaded plan to be dragged
    const planToDrag = await page.getByAltText('Thumbnail of plan').first();
  
    // Trigger a drag event on a preloaded plan
    await planToDrag.dispatchEvent('dragend');
  
    // The plan should be shown in the main section
    await expect(page.getByAltText(/Preview of the uploaded plan/)).toBeVisible();
  });

  test('Authenticated users can upload files', async ({ page }) => {
    await login(page);
    await expect(page.getByText(/Drop a plan here or click to upload/)).toBeVisible();

    // Ensure no query params after authentication
    const queryParams = page.url().split('?')[1]
    await expect(queryParams).toBeUndefined();
  });
});
