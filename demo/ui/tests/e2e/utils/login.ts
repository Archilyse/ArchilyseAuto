import { expect } from '@playwright/test';

const WAIT_UI_TO_REFRESH_MS = 3000; // Otherwise browser in headless mode can proceed without the dom changing

export default async function login(page) {
  await page.getByRole('button', {name: 'Login'}).click();

  await page.getByLabel(/Email address/).fill(process.env.AUTH0_TEST_USERNAME);
  await page.getByLabel(/Password/).fill(process.env.AUTH0_TEST_PASSWORD);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', {name: 'Login'})).not.toBeVisible({timeout: WAIT_UI_TO_REFRESH_MS});
}
