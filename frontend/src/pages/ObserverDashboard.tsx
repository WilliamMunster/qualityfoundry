/**
 * 上帝视角 (Observer) 监控看板
 */
import React, { useEffect, useState } from "react";
import { Card, Row, Col, Select, Button, Space, Typography, Tag, Divider, Empty, Spin } from "antd";
import { message } from "../components/AntdGlobal";
import {
    EyeOutlined,
    CheckCircleOutlined,
    SafetyCertificateOutlined,
    BulbOutlined,
    SyncOutlined
} from "@ant-design/icons";
import apiClient from "../api/client";
import { getRequirements, type Requirement } from "../api/requirements";

const { Title, Paragraph, Text } = Typography;

const ObserverDashboard: React.FC = () => {
    const [requirements, setRequirements] = useState<Requirement[]>([]);
    const [aiConfigs, setAiConfigs] = useState<any[]>([]);
    const [selectedReq, setSelectedReq] = useState<string | null>(null);
    const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [analyzing, setAnalyzing] = useState<Record<string, boolean>>({});
    const [results, setResults] = useState<Record<string, any>>({});

    useEffect(() => {
        loadRequirements();
        loadAiConfigs();
    }, []);

    const loadRequirements = async () => {
        try {
            const data = await getRequirements({ page: 1, page_size: 50 });
            setRequirements(data.items || []);
        } catch (error) {
            console.error("加载需求失败");
        }
    };

    const loadAiConfigs = async () => {
        try {
            const data: any = await apiClient.get("/api/v1/ai-configs");
            setAiConfigs(data || []);
        } catch (error) {
            console.error("加载 AI 配置失败");
        }
    };

    const handleAction = async (action: 'consistency' | 'coverage' | 'suggestions') => {
        if (!selectedReq) {
            message.warning("请先选择需求");
            return;
        }

        setAnalyzing(prev => ({ ...prev, [action]: true }));
        try {
            const endpoint = {
                consistency: `/api/v1/observer/consistency/${selectedReq}`,
                coverage: `/api/v1/observer/coverage/${selectedReq}`,
                suggestions: `/api/v1/observer/suggestions/${selectedReq}`,
            }[action];

            const params: any = {};
            if (selectedConfig) {
                params.config_id = selectedConfig;
            }

            const data: any = await apiClient.get(endpoint, { params });
            setResults(prev => ({ ...prev, [action]: data }));
            message.success("分析完成");
        } catch (error: any) {
            console.error(`${action} analysis failed`, error);
            const errorMsg = error.response?.data?.detail || "分析请求失败，请检查 AI 配置";
            message.error(`分析失败: ${errorMsg}`);
        } finally {
            setAnalyzing(prev => ({ ...prev, [action]: false }));
        }
    };

    const renderResult = (data: any, type: string) => {
        if (!data) return <Empty description="暂无数据，请点击分析" />;

        const content = data.analysis || data.coverage_analysis || data.suggestions;

        return (
            <div style={{ whiteSpace: 'pre-wrap', maxHeight: 400, overflowY: 'auto', padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                <Paragraph>{content}</Paragraph>
            </div>
        );
    };

    return (
        <div style={{ padding: '0 0 24px 0' }}>
            <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Title level={2}><EyeOutlined /> 上帝视角 (Observer)</Title>
                <Space>
                    <Select
                        placeholder="选择 AI 配置 (可选)"
                        style={{ width: 220 }}
                        allowClear
                        value={selectedConfig}
                        onChange={setSelectedConfig}
                        options={aiConfigs.map(c => ({
                            label: `${c.name} (${c.model})`,
                            value: c.id
                        }))}
                    />
                    <Select
                        placeholder="选择需求进行全链路分析"
                        style={{ width: 300 }}
                        value={selectedReq}
                        onChange={setSelectedReq}
                        options={requirements.map(r => ({ label: r.title, value: r.id }))}
                    />
                    <Button
                        icon={<SyncOutlined />}
                        onClick={() => { setSelectedReq(null); setSelectedConfig(null); setResults({}); }}
                    >
                        重置
                    </Button>
                </Space>
            </div>

            <Row gutter={[16, 16]}>
                <Col span={8}>
                    <Card
                        title={<span><SafetyCertificateOutlined style={{ color: '#1890ff' }} /> 一致性检查</span>}
                        extra={
                            <Button
                                type="primary"
                                size="small"
                                disabled={!selectedReq}
                                loading={analyzing.consistency}
                                onClick={() => handleAction('consistency')}
                            >
                                开始分析
                            </Button>
                        }
                    >
                        {renderResult(results.consistency, 'consistency')}
                    </Card>
                </Col>
                <Col span={8}>
                    <Card
                        title={<span><CheckCircleOutlined style={{ color: '#52c41a' }} /> 覆盖度评估</span>}
                        extra={
                            <Button
                                type="primary"
                                size="small"
                                disabled={!selectedReq}
                                loading={analyzing.coverage}
                                onClick={() => handleAction('coverage')}
                            >
                                开始评估
                            </Button>
                        }
                    >
                        {renderResult(results.coverage, 'coverage')}
                    </Card>
                </Col>
                <Col span={8}>
                    <Card
                        title={<span><BulbOutlined style={{ color: '#faad14' }} /> 全局改进建议</span>}
                        extra={
                            <Button
                                type="primary"
                                size="small"
                                disabled={!selectedReq}
                                loading={analyzing.suggestions}
                                onClick={() => handleAction('suggestions')}
                            >
                                获取建议
                            </Button>
                        }
                    >
                        {renderResult(results.suggestions, 'suggestions')}
                    </Card>
                </Col>
            </Row>

            <Card title="AI 执行诊断历史 (上帝视角监控)" style={{ marginTop: 24 }}>
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Paragraph type="secondary">
                        当测试执行失败时，上帝视角会自动介入分析。您可以在“执行管理”详情页中查看具体的 AI 诊断结果。
                    </Paragraph>
                    <Button onClick={() => window.location.href = '/executions'}>前往执行管理</Button>
                </div>
            </Card>
        </div>
    );
};

export default ObserverDashboard;
