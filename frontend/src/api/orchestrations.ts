/**
 * 编排执行 API
 */
import apiClient from './client';

export interface RunSummary {
    run_id: string;
    started_at: string;
    finished_at?: string;
    decision?: string;
    decision_source?: string;
    tool_count: number;
}

export interface RunsListResponse {
    runs: RunSummary[];
    count: number;
    total: number;
}

export interface OrchestrationRequest {
    nl_input: string;
    environment_id?: string;
    options?: {
        tool_name: string;
        args: Record<string, any>;
        timeout_s?: number;
        dry_run?: boolean;
    };
}

export interface OrchestrationResponse {
    run_id: string;
    decision: string;
    reason: string;
    evidence: any;
    links: {
        execution_id?: string;
        approval_id?: string;
        report_url?: string;
    };
}

const orchestrationsApi = {
    /**
     * 获取运行列表
     */
    listRuns: (params: { limit?: number; offset?: number } = {}): Promise<RunsListResponse> => {
        return apiClient.get('/api/v1/orchestrations/runs', { params });
    },

    /**
     * 发起编排运行
     */
    run: (data: OrchestrationRequest): Promise<OrchestrationResponse> => {
        return apiClient.post('/api/v1/orchestrations/run', data);
    },

    /**
     * 获取证据文件
     */
    getEvidence: (runId: string): Promise<any> => {
        return apiClient.get(`/api/v1/artifacts/${runId}/evidence.json`);
    },

    /**
     * 获取审计日志
     */
    getAudit: (runId: string): Promise<{ run_id: string; events: any[]; audit_enabled: boolean }> => {
        return apiClient.get(`/api/v1/audit/${runId}`);
    },
};

export default orchestrationsApi;
