import React, { useEffect, useState } from 'react';
import { Card, Steps, Tag, Typography, Space } from 'antd';
import { CheckCircle2, XCircle, AlertCircle, ShieldCheck, Globe, Library } from 'lucide-react';
import { getEnvironments } from '../api/environments';
import orchestrationsApi from '../api/orchestrations';

const { Text } = Typography;

interface CheckStatus {
    status: 'wait' | 'process' | 'finish' | 'error';
    message: string;
}

const ReadinessCheck: React.FC = () => {
    const [envStatus, setEnvStatus] = useState<CheckStatus>({ status: 'process', message: '检查中...' });
    const [policyStatus, setPolicyStatus] = useState<CheckStatus>({ status: 'wait', message: '等待环境检查...' });
    const [authStatus, setAuthStatus] = useState<CheckStatus>({ status: 'wait', message: '等待配置检查...' });

    useEffect(() => {
        const checkReadiness = async () => {
            // 1. Environments Check
            try {
                const envRes = await getEnvironments();
                if (envRes.items.length > 0) {
                    setEnvStatus({ status: 'finish', message: `已找到 ${envRes.items.length} 个环境` });
                } else {
                    setEnvStatus({ status: 'error', message: '未初始化环境 (Local seed未生效)' });
                    return;
                }
            } catch (error) {
                setEnvStatus({ status: 'error', message: '环境接口调用失败' });
                return;
            }

            // 2. Policies Check
            setPolicyStatus({ status: 'process', message: '检查中...' });
            try {
                const policyRes = await orchestrationsApi.getCurrentPolicy();
                if (policyRes && policyRes.version) {
                    setPolicyStatus({ status: 'finish', message: `策略库就绪 (v${policyRes.version})` });
                } else {
                    setPolicyStatus({ status: 'error', message: '策略库为空/未加载' });
                    return;
                }
            } catch (error: any) {
                if (error.response?.status === 404) {
                    setPolicyStatus({ status: 'error', message: '策略库为空/未加载' });
                } else {
                    setPolicyStatus({ status: 'error', message: '策略接口异常' });
                }
                return;
            }

            // 3. Auth Check
            setAuthStatus({ status: 'process', message: '检查中...' });
            try {
                await orchestrationsApi.listRuns({ limit: 1 });
                setAuthStatus({ status: 'finish', message: '认证已就绪' });
            } catch (error: any) {
                if (error.response?.status === 401) {
                    setAuthStatus({ status: 'error', message: '需要登录 (符合预期)' });
                } else {
                    setAuthStatus({ status: 'error', message: '认证状态异常' });
                }
            }
        };

        checkReadiness();
    }, []);

    const getIcon = (status: string) => {
        switch (status) {
            case 'finish': return <CheckCircle2 size={16} className="text-green-500" />;
            case 'error': return <XCircle size={16} className="text-red-500" />;
            case 'process': return <AlertCircle size={16} className="text-blue-500" />;
            default: return <AlertCircle size={16} className="text-gray-300" />;
        }
    };

    return (
        <Card
            size="small"
            title={<Space><ShieldCheck size={18} className="text-blue-600" /> <Text strong>运行环境就绪检查 (Readiness Check)</Text></Space>}
            style={{ marginBottom: 24, borderRadius: 12, border: '1px solid #e5e7eb' }}
            id="readiness-check-card"
        >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    data-testid="readiness-item-environment"
                    data-status={envStatus.status}
                >
                    <Space>
                        <Globe size={14} className="text-gray-400" />
                        <Text>运行环境 (Environments)</Text>
                    </Space>
                    <Tag icon={getIcon(envStatus.status)} color={envStatus.status === 'finish' ? 'success' : (envStatus.status === 'error' ? 'error' : 'default')}>
                        {envStatus.message}
                    </Tag>
                </div>
                <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    data-testid="readiness-item-policy"
                    data-status={policyStatus.status}
                >
                    <Space>
                        <Library size={14} className="text-gray-400" />
                        <Text>核心策略 (Policy Library)</Text>
                    </Space>
                    <Tag icon={getIcon(policyStatus.status)} color={policyStatus.status === 'finish' ? 'success' : (policyStatus.status === 'error' ? 'error' : 'default')}>
                        {policyStatus.message}
                    </Tag>
                </div>
                <div
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    data-testid="readiness-item-auth"
                    data-status={authStatus.status}
                >
                    <Space>
                        <ShieldCheck size={14} className="text-gray-400" />
                        <Text>认证状态 (Authentication State)</Text>
                    </Space>
                    <Tag icon={getIcon(authStatus.status)} color={authStatus.status === 'finish' ? 'success' : (authStatus.status === 'error' ? 'warning' : 'default')}>
                        {authStatus.message}
                    </Tag>
                </div>
            </div>
        </Card>
    );
};

export default ReadinessCheck;
