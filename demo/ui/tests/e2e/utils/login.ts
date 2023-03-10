export default async function login(page) {
  await page.getByRole('button', {name: 'Login'}).click();

  await page.getByLabel(/Email address/).fill(process.env.AUTH0_TEST_USERNAME);
  await page.getByLabel(/Password/).fill(process.env.AUTH0_TEST_PASSWORD);
  await page.keyboard.press('Enter');
}