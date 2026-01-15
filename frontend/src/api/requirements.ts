/**
 * 需求管理 API
 */
import apiClient from './client';

export interface Requirement {
  id: string;
  title: string;
  content: string;
  version: string;
  file_path?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RequirementCreate {
  title: string;
  content: string;
  version: string;
}

export interface RequirementList {
  total: number;
  items: Requirement[];
  page: number;
  page_size: number;
}

/**
 * 获取需求列表
 */
export const getRequirements = async (params?: {
  page?: number;
  page_size?: number;
  search?: string;
}): Promise<RequirementList> => {
  return apiClient.get('/api/v1/requirements', { params });
};

/**
 * 获取需求详情
 */
export const getRequirement = async (id: string): Promise<Requirement> => {
  return apiClient.get(`/api/v1/requirements/${id}`);
};

/**
 * 创建需求
 */
export const createRequirement = async (data: RequirementCreate): Promise<Requirement> => {
  return apiClient.post('/api/v1/requirements', data);
};

/**
 * 更新需求
 */
export const updateRequirement = async (
  id: string,
  data: Partial<RequirementCreate>
): Promise<Requirement> => {
  return apiClient.put(`/api/v1/requirements/${id}`, data);
};

/**
 * 删除需求
 */
export const deleteRequirement = async (id: string): Promise<void> => {
  return apiClient.delete(`/api/v1/requirements/${id}`);
};

/**
 * 批量删除需求
 */
export const batchDeleteRequirements = async (ids: string[]): Promise<void> => {
  return apiClient.post('/api/v1/requirements/batch-delete', { ids });
};

/**
 * 上传需求文档
 */
export const uploadRequirement = async (file: File): Promise<Requirement> => {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiClient.post('/api/v1/upload/requirement', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
