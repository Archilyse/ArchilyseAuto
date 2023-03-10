import { test, expect } from '@playwright/test';

test.beforeEach(async ({page}) => {
  await page.goto('/')
})

test.describe('Preload plans examples', () => {
  test('Randomly display the right number of plans', async ({page}) => {
    const planCount = await page.getByAltText('Thumbnail of plan').count()
    await expect(planCount).toBe(3);
  });
})