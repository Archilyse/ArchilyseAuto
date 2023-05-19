export default async  function (page, context) {
  const popupPromise = context.waitForEvent('page');

  await page.getByText(/Log in/).click();

  const popup = await popupPromise;

  await popup.getByLabel(/Email address/).fill(process.env.AUTH0_TEST_USERNAME);
  await popup.getByLabel(/Password/).fill(process.env.AUTH0_TEST_PASSWORD);
  await popup.keyboard.press('Enter');
}

