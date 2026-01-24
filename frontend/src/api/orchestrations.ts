/**
 * 编排执行 API
 * 
 * Contract Snapshot: v1.0 (2026-01-24)
 * 对应后端: routes_orchestrations.py, routes_policies.py
 */
import apiClient from './client';

// ============== Runs List ==============

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

// ============== Run Detail (P1 DTO) ==============

export interface OwnerInfo {
    user_id?: string;
    username?: string;
}

export interface PolicyMeta {
    version?: string;
    hash?: string;
}

export interface ReproMeta {
    git_sha?: string;
    branch?: string;
    dirty: boolean;
    deps_fingerprint?: string;
}

export interface GovernanceDTO {
    budget: Record<string, any>;
    short_circuited: boolean;
    short_circuit_reason?: string;
    decision_source?: string;
}

export interface ArtifactInfo {
    type: string;
    path: string;  // 相对路径，不含绝对路径
    size?: number;
    mime?: string;
}

export interface AuditSummary {
    event_count: number;
    first_at?: string;
    last_at?: string;
}

export interface SummaryInfo {
    started_at?: string;
    finished_at?: string;
    ok?: boolean;
    decision?: string;
    decision_source?: string;
    tool_count: number;
}

export interface RunDetail {
    run_id: string;
    owner?: OwnerInfo;
    summary: SummaryInfo;
    policy?: PolicyMeta;
    repro?: ReproMeta;
    governance?: GovernanceDTO;
    artifacts: ArtifactInfo[];
    audit_summary?: AuditSummary;  // 仅 ADMIN 可见
}

// ============== Policies ==============

export interface PolicyInfo {
    version: string;
    policy_hash: string;
    git_sha?: string;
    deps_fingerprint?: string[];
    source: string;
    summary: {
        high_risk_keywords_count: number;
        high_risk_patterns_count: number;
        tools_allowlist_count: number;
        cost_governance: {
            timeout_s: number;
            max_retries: number;
        };
    };
}

// ============== Orchestration Request/Response ==============

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

// ============== API Methods ==============

const orchestrationsApi = {
    /**
     * 获取运行列表
     */
    listRuns: (params: { limit?: number; offset?: number } = {}): Promise<RunsListResponse> => {
        return apiClient.get('/api/v1/orchestrations/runs', { params });
    },

    /**
     * 获取运行详情 (P1 RunDetail DTO)
     */
    getRunDetail: (runId: string): Promise<RunDetail> => {
        return apiClient.get(`/api/v1/orchestrations/runs/${runId}`);
    },

    /**
     * 发起编排运行
     */
    run: (data: OrchestrationRequest): Promise<OrchestrationResponse> => {
        return apiClient.post('/api/v1/orchestrations/run', data);
    },

    /**
     * 获取证据文件 (Legacy - 推荐使用 getRunDetail)
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

    /**
     * 获取当前策略配置
     */
    getCurrentPolicy: (): Promise<PolicyInfo> => {
        return apiClient.get('/api/v1/policies/current');
    },
};

export default orchestrationsApi;

