import path from 'path';
import { fileURLToPath } from 'url';
import { test, expect } from '@playwright/test';
import login from './utils/login.js';
import uploadFile from './utils/uploadFile.js';
// Need to get the correct filename otherwise tests may fail, and __dirname is not available when using ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SAMPLE_PLAN = path.resolve(__dirname, '../fixtures/sample_plan.jpg');
const WRONG_FILE = path.resolve(__dirname, '../fixtures/wrong_file.png');

const UPLOAD_TIMEOUT_MS = 700 * 1000; // 11 min
const DRAG_TIMEOUT_MS = 5000; // 5 seconds

test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await login(page);
});



async function assertPlanUploaded  (page)  {
    await expect(page.getByAltText(/Processed walls of the uploaded plan/)).toBeVisible({ timeout: UPLOAD_TIMEOUT_MS });
    await expect(page.getByAltText(/Processed features of the uploaded plan/)).toBeVisible({ timeout: UPLOAD_TIMEOUT_MS });
}

test.describe.skip('Plan upload', () => {
    test.setTimeout(UPLOAD_TIMEOUT_MS * 3);

    test.describe('Using the file dropzone', () => {
        test('Uploads a plan successfully', async ({ page, browserName }) => {
            await uploadFile(page, browserName, SAMPLE_PLAN);

            await expect(page.getByText(/Loading.../)).toBeVisible();
            await assertPlanUploaded(page)
            //@TODO ensure input is not enabled
        });

        test.skip('Dragging and dropping a preloaded plan to the file dropzone', async ({ page, browserName }) => {
            // Find the plan to be dragged
            const planToDrag = await page.getByAltText('Thumbnail of plan').first();

            // Find the drop area
            const dropArea = await page.getByText(/Drop a plan here or click to upload/);

            // Perform the drag and drop
            await planToDrag.dragTo(dropArea, {timeout: DRAG_TIMEOUT_MS});

            // Verify that the image was successfully dropped & processed
            await assertPlanUploaded(page)
        });

        test('A failure shows an error message', async ({ page, browserName }) => {
            await uploadFile(page, browserName, WRONG_FILE);
            
            await expect(page.getByText(/Error uploading the file/)).toBeVisible({ timeout: UPLOAD_TIMEOUT_MS });
        });
    });

    test.skip('Using a preloaded plan', async ({ page }) => {
        await page.getByAltText('Thumbnail of plan').first().click();
        await assertPlanUploaded(page)
    });
});
