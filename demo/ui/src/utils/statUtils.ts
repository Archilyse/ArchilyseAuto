import capitalize from "./capitalize";

const filterObjectByKey = (object, filter) => {
    return Object.entries(object).reduce((accum, [key, value]) => {
        if (value > 0 && key.includes(filter)) {
            const label = capitalize(key.replace(filter, ""));
            accum[label] = value;
        }
        return accum;
    }, {});
};

const sum = (object): any => Object.values(object).reduce((accum: number, value: number) => accum + value, 0);

// This functions compute intervals like [0, X], [X, Y], [Y, Z] (e.g. [0,10],[10, 100],[100,150])...
const computeConsecutiveIntervals = (stats) => {
    let previousOne;
    const intervals = Object.entries(stats).reduce((accum, [key, value], index) => {
        if (index === 0) {
            accum[key] = [0, value];
            previousOne = value;
        } else {
            const nextOne = previousOne + value;
            accum[key] = [previousOne, nextOne];
            previousOne = nextOne;
        }
        return accum;
    }, {});
    return intervals;
};

const getCountStats = (statistics) => {
    return filterObjectByKey(statistics, "_count");
};

const getAreaStats = (statistics) => {
    const rawSpaceStats = filterObjectByKey(statistics, "_space");
    const spaceStats = Object.entries(rawSpaceStats).reduce((accum, [key, value]: [string, number]) => {
        accum[key] = parseFloat(value.toFixed(2));
        return accum;
    }, {});

    const areaDataIntervals = computeConsecutiveIntervals(spaceStats);

    const subtotal = parseFloat(sum(spaceStats).toFixed(2));
    areaDataIntervals["Subtotal"] = [0, subtotal];
    return areaDataIntervals;
};

export default {
    getCountStats,
    getAreaStats,
};
