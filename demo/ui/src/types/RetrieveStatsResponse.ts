export type RetrieveStatsResponse = {
    status: 'READY' | 'NOT_READY';
    statistics: {
        door_count: number;
        window_count: number;
        toilet_count: number;
        bathtub_count: number;
        sink_count: number;
        shower_count: number;
        wall_space: number;
        railing_space: number;
        door_space: number;
        window_space: number;
        toilet_space: number;
        bathtub_space: number;
        sink_space: number;
        shower_space: number;
    };
};
