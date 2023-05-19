import { test, expect, describe, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import request from '../../src/providers/request';
import { processedIcons, processedWalls, processedSpaces, wallTimer, iconTimer, spacesTimer, backgroundTimer, statisticsTimer, processedBackground, processedStats } from '../../src/stores';
import uploadPlan from '../../src/utils/uploadPlan.js';
import { RequestPredictionResponse } from '../../src/types';
import TaskStatus from '../../src/types/TaskStatus';

const MOCK_FILE = new File(
    ['A payaso mock'],
    'actually this should be an image but it does not matter for the mock.txt'
);
const FAKE_IMG_URL = 'http://fake-image-blob-url';

vi.stubGlobal('URL', { createObjectURL: () => FAKE_IMG_URL });

const mockResultsReady = () => {
    vi.spyOn(request, 'get').mockImplementation(async (url, options: any): Promise<any> => {
        return { data: 'fakeimg', status: 200 };
    });
};

const mockUploadImage = () => {
    vi.spyOn(request, 'put').mockImplementation(async (url, options: any): Promise<any> => {
        return { status: 200 };
    });
}

const mockRequestPrediction = () => {
    const mockResponse = async (url:string, data: any, options: any): Promise<{data: RequestPredictionResponse}> => {
        return { data: { wall_task: { id: '1', status: TaskStatus.STARTED, }, icon_task: { id: '2', status: TaskStatus.STARTED },
        spaces_task: { id: '3', status: TaskStatus.PENDING }, background_task: { id: '4', status: TaskStatus.PENDING }, statistics_task: { id: '5', status: TaskStatus.STARTED } } };
    };
    // @ts-ignore
    vi.spyOn(request, 'post').mockImplementation(mockResponse); // Ignore so TS doesn't complain we don't respond all axios (status, config...) response
};

const assertSVGImage = (expectedURL: string | null) => {
    expect(get(processedIcons)).toBe(expectedURL);
    expect(get(processedWalls)).toBe(expectedURL);
    expect(get(processedSpaces)).toBe(expectedURL);
    expect(get(processedBackground)).toBe(expectedURL);
};

const assertTimersAreNull = () => {
    expect(get(wallTimer)).toBe(null);
    expect(get(iconTimer)).toBe(null);
    expect(get(spacesTimer)).toBe(null);
    expect(get(backgroundTimer)).toBe(null);
    expect(get(statisticsTimer)).toBe(null);
};
const resetSVGImage = () => {
    processedIcons.set(null);
    processedWalls.set(null);
    processedSpaces.set(null);
    processedBackground.set(null);
};

describe('uploadPlan', () => {
    let mockActiveTimers;

    beforeEach(() => {
        resetSVGImage();
        mockUploadImage();
        mockRequestPrediction();

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

    test('Uploading a plans successfully sets: Icons, walls, spaces, background & stats', async () => {
        mockResultsReady();

        assertSVGImage(null);
        await uploadPlan(MOCK_FILE);
        assertSVGImage(FAKE_IMG_URL);

        // stats will the value of the request.get mock above, so for simplicity we assert that it has been set (not initial value, null)
        expect(get(processedStats)).not.toBeNull();
    });

    test('After receiving results, timer are reset', async () => {
        mockResultsReady();

        assertTimersAreNull();
        await uploadPlan(MOCK_FILE);
        assertTimersAreNull();
    });

    test('If there is an error, timers are reset', async () => {
        vi.spyOn(request, 'get').mockImplementation(async (url, options: any): Promise<any> => {
            throw new Error('something went wrong');
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
