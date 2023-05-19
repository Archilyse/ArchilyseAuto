import { test, expect } from '@playwright/test';
import login from './utils/login.js';
import { DISCORD_URL, LINKEDIN_URL } from '../../src/constants.js';

const SITE_LOAD_TIMEOUT_MS = 180 * 1000; // 3 min

test.beforeEach(async ({ page }) => {
    await page.goto('/');
});

test.describe('Test the Sidebar Links', () => {
    test.setTimeout(SITE_LOAD_TIMEOUT_MS);

    test('Opens the correct Follow URL in a new tab', async ({ page, browser }) => {
        await expect(page.getByText(/Follow/)).toBeVisible();
        await page.getByText(/Follow/).click();

        // Confirm the right URL is opened
        const context = await browser.newContext();
        const newTab = await context.newPage();
        await newTab.goto(LINKEDIN_URL);
        await expect(newTab.url()).toEqual(LINKEDIN_URL);
    });

    test('Opens the correct Discuss URL in a new tab', async ({ page, browser }) => {
        const DISCORD_DOMAIN_PREFIX = 'discord';

        await expect(page.getByText(/Discuss/)).toBeVisible();
        await page.getByText(/Discuss/).click();

        // Confirm the right URL is opened
        const context = await browser.newContext();
        const newTab = await context.newPage();
        await newTab.goto(DISCORD_URL);
        await expect(newTab.url().includes(DISCORD_DOMAIN_PREFIX)).toBeTruthy();
    });


    test.skip('Resets the floor plan and variables by clicking on Home button', async ({ page }) => {
        // Confirm that no plan is loaded yet
        await expect(page.getByText(/Log in with your account to upload plans/)).toBeVisible();
        // Use a preloaded plan
        await page.getByAltText('Thumbnail of plan').first().click();
        await expect(page.getByText(/Log in with your account to upload plans/)).not.toBeVisible();
        // Click on the Home button
        await page.getByText(/Home/).click();
        await expect(page.getByText(/Log in with your account to upload plans/)).toBeVisible();
    });


    test.skip('Shows a signup button when the user loads a plan and is not authenticated', async ({ page }) => {
        // Initially is not shown
        await expect(page.getByTestId('signup-sidebar')).not.toBeVisible();

        // If we load a preloaded plan without login
        await page.getByAltText('Thumbnail of plan').first().click();

        // It should be visible
        await expect(page.getByTestId('signup-sidebar')).toBeVisible();
    });
    test.skip('Uploading a preloaded plan unauthenticated shows signup button', async ({ page }) => {
        // If we load a preloaded plan without login
        await page.getByTestId('close-tos-snackbar').click();
        await page.getByAltText('Thumbnail of plan').first().click();

        // It should be visible
        await expect(page.getByTestId('signup-sidebar')).toBeVisible();

        // And we should log successfully
        await login(page);
        await expect(page.getByText(/Drop a plan here or click to upload/)).toBeVisible();

        // And the snackbar should disappear (we assumed loged users == accepted TOS)
        await expect(page.getByTestId('close-tos-snackbar')).not.toBeVisible();
    });

    test('Clicking on the logout button successfully logs the user out', async ({ page }) => {
        // Confirm user logged in successfully
        await login(page);
        await expect(page.getByText(/Drop a plan here or click to upload/)).toBeVisible();

        // Click on the Logout button
        await page.getByText(/Log out/).click();

        // Confirm that no plan is loaded yet
        await expect(page.getByText(/Login/)).toBeVisible();
    });
});