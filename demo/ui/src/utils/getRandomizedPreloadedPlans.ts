const getRandomizedPreloadedPlans = (preloadedPlans: string[]) => {
    const randomize = preloadedPlans.sort(() => Math.random() - 0.5);
    return randomize.slice(0, 3);
};

export default getRandomizedPreloadedPlans;
