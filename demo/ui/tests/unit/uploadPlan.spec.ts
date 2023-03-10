import { test, expect, describe, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import request from '../../src/providers/request';
import { processedIcons, processedWalls, processedSpaces, wallTimer, iconTimer } from '../../src/stores';
import uploadPlan from '../../src/utils/uploadPlan.js';

// @TODO: Extend this tests to test the background fetch that happens inside uploadPlan
const MOCK_FILE = new File(
    ['A payaso mock'],
    'actually this should be an image but it does not matter for the mock.txt'
);
const FAKE_IMG_URL = 'http://fake-image-blob-url';

vi.stubGlobal('URL', { createObjectURL: () => FAKE_IMG_URL });

const mockResultsReady = () => {
    vi.spyOn(request, 'get').mockImplementation(async (url, options: any): Promise<any> => {
        return { data: 'fakeimg', headers: { 'content-type': 'image/svg' } };
    });
};

const mockUploadImageResponse = () => {
    vi.spyOn(request, 'post').mockImplementation(async (url, data, options: any): Promise<any> => {
        return { data: { wall_task: { id: 1, status: '' }, icon_task: { id: 2, status: 'ola' }, spaces_task: { id: 3, status: 'merhaba' } } };
    });
};

const assertSVGImage = (expectedURL: string | null) => {
    expect(get(processedIcons)).toBe(expectedURL);
    expect(get(processedWalls)).toBe(expectedURL);
    expect(get(processedSpaces)).toBe(expectedURL);
};

const assertTimersAreNull = () => {
    expect(get(wallTimer)).toBe(null);
    expect(get(iconTimer)).toBe(null);
};
const resetSVGImage = () => {
    processedIcons.set(null);
    processedWalls.set(null);
    processedSpaces.set(null);
};

describe('uploadPlan', () => {
    let mockActiveTimers;

    beforeEach(() => {
        resetSVGImage();
        mockUploadImageResponse();

        mockActiveTimers = 0;
        vi.spyOn(global, 'setInterval').mockImplementation((fn): any => {
            mockActiveTimers++;
            fn();
        });
        vi.spyOn(global, 'clearInterval').mockImplementation((fn): any => {
            if (mockActiveTimers === 0) return;
            mockActiveTimers--;
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    test('Uploading a plans successfully set icons & walls image', async () => {
        mockResultsReady();

        assertSVGImage(null);
        await uploadPlan(MOCK_FILE);
        assertSVGImage(FAKE_IMG_URL);
    });

    test('After receiving results, timer are reset', async () => {
        mockResultsReady();

        assertTimersAreNull();
        await uploadPlan(MOCK_FILE);
        assertTimersAreNull();
    });

    test('If there is an error, timers are reset', async () => {
        vi.spyOn(request, 'get').mockImplementation(async (url, options: any): Promise<any> => {
            return {
                data: 'this will throw an error as it is not what fetchData expects',
                headers: { 'content-type': 'application/json' },
            };
        });

        assertTimersAreNull();
        await expect(uploadPlan(MOCK_FILE)).rejects.toThrowError();
        assertTimersAreNull();
    });

    test('Asking for results repeatedly does not create additional polling timers', async () => {
        mockResultsReady();

        // Upload a plan without waiting for the result
        uploadPlan(MOCK_FILE);
        // Upload again and wait this time
        await uploadPlan(MOCK_FILE);

        //All timers should be cancelled properly, otherwise it means there are timers still polling from the first request (which was not "waited")
        expect(mockActiveTimers).toBe(0);
    });
});
