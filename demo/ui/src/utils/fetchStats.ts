import { ENDPOINTS } from '../constants';
import { request } from '../providers';
import type { RetrieveStatsBody } from '../types';
import type { RetrieveStatsResponse } from '../types/RetrieveStatsResponse';

const fetchStats = async (taskIds: RetrieveStatsBody): Promise<RetrieveStatsResponse> => {
  const response: { data: RetrieveStatsResponse; } = await request.post(ENDPOINTS.RETRIEVE_STATS, taskIds);
  if (response.data?.status === "READY") return response.data;
  return null;
};

export default fetchStats;
