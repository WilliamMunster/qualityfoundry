/**
 * 场景管理 API
 */
import apiClient from './client';

export interface Scenario {
  id: string;
  requirement_id: string;
  title: string;
  description?: string;
  steps: string[];
  approval_status: string;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  requirement_id: string;
  title: string;
  description?: string;
  steps: string[];
}

export interface ScenarioList {
  total: number;
  items: Scenario[];
  page: number;
  page_size: number;
}

export const getScenarios = async (params?: {
  requirement_id?: string;
  approval_status?: string;
  page?: number;
  page_size?: number;
}): Promise<ScenarioList> => {
  return apiClient.get('/api/v1/scenarios', { params });
};

export const getScenario = async (id: string): Promise<Scenario> => {
  return apiClient.get(`/api/v1/scenarios/${id}`);
};

export const createScenario = async (data: ScenarioCreate): Promise<Scenario> => {
  return apiClient.post('/api/v1/scenarios', data);
};

export const generateScenarios = async (data: {
  requirement_id: string;
  auto_approve?: boolean;
}): Promise<Scenario[]> => {
  return apiClient.post('/api/v1/scenarios/generate', data);
};

export const approveScenario = async (id: string, reviewer: string, comment?: string): Promise<Scenario> => {
  return apiClient.post(`/api/v1/scenarios/${id}/approve`, { reviewer, comment });
};

export const rejectScenario = async (id: string, reviewer: string, comment?: string): Promise<Scenario> => {
  return apiClient.post(`/api/v1/scenarios/${id}/reject`, { reviewer, comment });
};

export const batchDeleteScenarios = async (ids: string[]): Promise<void> => {
  return apiClient.post('/api/v1/scenarios/batch-delete', { ids });
};
