/**
 * 用例管理 API
 */
import apiClient from './client';

export interface TestCase {
  id: string;
  seq_id?: number;
  scenario_id: string;
  scenario_seq_id?: number;
  title: string;
  preconditions: string[];
  steps: string[];
  expected_results: string[];
  approval_status: string;
  created_at: string;
  updated_at: string;
}

export interface TestCaseCreate {
  scenario_id: string;
  title: string;
  preconditions?: string[];
  steps: string[];
  expected_results?: string[];
}

export interface TestCaseList {
  total: number;
  items: TestCase[];
  page: number;
  page_size: number;
}

export const getTestCases = async (params?: {
  scenario_id?: string;
  approval_status?: string;
  page?: number;
  page_size?: number;
}): Promise<TestCaseList> => {
  return apiClient.get('/api/v1/testcases', { params });
};

export const getTestCase = async (id: string): Promise<TestCase> => {
  return apiClient.get(`/api/v1/testcases/${id}`);
};

export const createTestCase = async (data: TestCaseCreate): Promise<TestCase> => {
  return apiClient.post('/api/v1/testcases', data);
};

export const generateTestCases = async (data: {
  scenario_id: string;
  auto_approve?: boolean;
}): Promise<TestCase[]> => {
  return apiClient.post('/api/v1/testcases/generate', data);
};

export const approveTestCase = async (id: string, reviewer: string, comment?: string): Promise<TestCase> => {
  return apiClient.post(`/api/v1/testcases/${id}/approve`, { reviewer, comment });
};

export const rejectTestCase = async (id: string, reviewer: string, comment?: string): Promise<TestCase> => {
  return apiClient.post(`/api/v1/testcases/${id}/reject`, { reviewer, comment });
};

export const batchDeleteTestCases = async (ids: string[]): Promise<void> => {
  return apiClient.post('/api/v1/testcases/batch-delete', { ids });
};
