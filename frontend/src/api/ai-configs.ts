/**
 * AI 配置 API
 */
import apiClient from './client';

export interface AIConfig {
    id: string;
    name: string;
    provider: string;
    model: string;
    api_key?: string;
    api_key_masked?: string;
    base_url?: string;
    assigned_steps?: string[];
    temperature: string;
    max_tokens: string;
    top_p: string;
    extra_params?: any;
    is_active: boolean;
    is_default: boolean;
    created_at: string;
}

export interface AIConfigCreate {
    name: string;
    provider: string;
    model: string;
    api_key: string;
    base_url?: string;
    assigned_steps?: string[];
    temperature: string;
    max_tokens: string;
    top_p?: string;
    is_default: boolean;
}

export interface AITestRequest {
    config_id?: string;
    prompt: string;
    provider?: string;
    model?: string;
    api_key?: string;
    base_url?: string;
}

export const getAIConfigs = async (params?: any) => {
    return apiClient.get('/api/v1/ai-configs', { params });
};

export const getAIConfig = async (id: string) => {
    return apiClient.get(`/api/v1/ai-configs/${id}`);
};

export const createAIConfig = async (data: AIConfigCreate) => {
    return apiClient.post('/api/v1/ai-configs', data);
};

export const updateAIConfig = async (id: string, data: any) => {
    return apiClient.put(`/api/v1/ai-configs/${id}`, data);
};

export const deleteAIConfig = async (id: string) => {
    return apiClient.delete(`/api/v1/ai-configs/${id}`);
};

export const testAIConfig = async (data: AITestRequest) => {
    return apiClient.post('/api/v1/ai-configs/test', data);
};

export interface AIExecutionLog {
    id: string;
    step?: string;
    config_id?: string;
    provider?: string;
    model?: string;
    request_messages?: any[];
    response_content?: string;
    status: string;
    error_message?: string;
    duration_ms?: number;
    created_at: string;
}

export const getAIExecutionLogs = async (params?: any) => {
    return apiClient.get('/api/v1/ai-configs/logs', { params });
};
