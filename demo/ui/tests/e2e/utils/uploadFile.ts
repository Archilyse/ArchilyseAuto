const clickOnDropzone = async (page, browserName) => {
    // Firefox crashes if we try to open an upload window in headless mode: https://github.com/testing-library/user-event/issues/824
    if (browserName !== 'firefox') {
        await page.getByText(/Drop a plan here or click to upload/).click();
    }
};

export default async function uploadFile(page, browserName, file) {
    await clickOnDropzone(page, browserName);
    await page.locator('input[name="file-dropzone"]').setInputFiles(file);
}