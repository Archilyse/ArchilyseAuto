import { test, expect, describe } from 'vitest';
import getRandomizedPreloadedPlans from '../../src/utils/getRandomizedPreloadedPlans.js';

const MOCK_PRELOADED_PLANS = ["sample_1.png", "sample_2.jpg", "sample_3.jpg", "sample_4.png", "sample_5.jpg", "sample_6.jpg", "sample_7.jpg", "sample_8.jpg", "sample_9.jpg", "sample_10.jpg"];

describe('getRandomizedPreloadedPlans', () => {
    test('Test if only 3 plans are displayed out of the total', () => {
        const result = getRandomizedPreloadedPlans(MOCK_PRELOADED_PLANS).length;
        expect(result).toBe(3);
    });
    
    test('Test if the returned set of plans is different each time the function is called', () => {
        let result1 = getRandomizedPreloadedPlans(MOCK_PRELOADED_PLANS);
        let result2 = getRandomizedPreloadedPlans(MOCK_PRELOADED_PLANS);
        expect(result1).not.toEqual(result2);
    });
});