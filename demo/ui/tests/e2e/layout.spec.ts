import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';
import login from './utils/login.js';
import uploadFile from './utils/uploadFile.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SAMPLE_PLAN = path.resolve(__dirname, '../fixtures/sample_plan.jpg');

test.beforeEach(async ({ page }) => {
    await page.goto('/');
});

const assertInitialInfo = async (page) => {
    await expect(page.getByText(/Examples/)).toBeVisible();
    await expect(page.getByText(/Capabilities/)).toBeVisible();
    await expect(page.getByText(/Limitations/)).toBeVisible();
};

test.describe('Main layout visibility', () => {
    test('If the user is not authenticated, it will see the info & prompt to autenticate', async ({ page }) => {
        await assertInitialInfo(page);
        await expect(page.getByText(/Log in with your account to upload plans/)).toBeVisible();
    });
    test('If the user is authenticated, it will see info & prompt to upload', async ({ page }) => {
        await login(page);
        await assertInitialInfo(page);
        await expect(page.getByText(/Drop a plan here or click to upload/)).not.toBeVisible();

    });
    test.skip('On uploading a plan only the plan image is shown', async ({ page, browserName }) => {
        await login(page);
        await uploadFile(page, browserName, SAMPLE_PLAN);

        await expect(page.getByText(/Examples/)).not.toBeVisible();
        await expect(page.getByText(/Drop a plan here or click to upload/)).not.toBeVisible();
        await expect(page.getByAltText(/Preview of the uploaded plan/)).toBeVisible();
    });

});