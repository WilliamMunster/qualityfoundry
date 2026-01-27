import React from 'react';
import { Card, Typography, Row, Col, Progress, Tooltip, Tag, Space } from 'antd';
import { ShieldCheck, Zap, AlertTriangle, FileCheck } from 'lucide-react';

const { Text, Title } = Typography;

interface Props {
    data?: {
        total_artifact_count: number;
        runs_with_artifact_count: number;
        truncated_runs_count: number;
    };
    totalRuns: number;
    loading?: boolean;
}

const EvidenceCoverageCard: React.FC<Props> = ({ data, totalRuns, loading }) => {
    const coveragePercent = totalRuns > 0 ? Math.round((data?.runs_with_artifact_count || 0) / totalRuns * 100) : 0;
    const explosionRisk = data?.truncated_runs_count || 0;

    return (
        <Card
            loading={loading}
            variant="outlined"
            style={{ borderRadius: 24, height: '100%', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
            bodyStyle={{ padding: '20px' }}
        >
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Space>
                        <div style={{ padding: 8, background: 'rgba(16, 185, 129, 0.1)', borderRadius: 12 }}>
                            <ShieldCheck size={20} className="text-emerald-500" />
                        </div>
                        <div>
                            <Title level={5} style={{ margin: 0 }}>证据覆盖率</Title>
                            <Text type="secondary" style={{ fontSize: '12px' }}>Evidence Coverage</Text>
                        </div>
                    </Space>
                    <Tag color="blue" bordered={false} style={{ borderRadius: 8 }}>P1 Metrics</Tag>
                </div>

                <Row gutter={24} align="middle">
                    <Col span={10}>
                        <Tooltip title={`${data?.runs_with_artifact_count || 0} / ${totalRuns} 运行已记录产物审计`}>
                            <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
                                <Progress
                                    type="dashboard"
                                    percent={coveragePercent}
                                    size={100}
                                    strokeColor={{
                                        '0%': '#10b981',
                                        '100%': '#3b82f6',
                                    }}
                                    format={(p) => (
                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                            <span style={{ fontSize: '18px', fontWeight: 600 }}>{p}%</span>
                                            <span style={{ fontSize: '10px', color: '#94a3b8' }}>覆盖</span>
                                        </div>
                                    )}
                                />
                            </div>
                        </Tooltip>
                    </Col>
                    <Col span={14}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <div>
                                <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>累计产物数</Text>
                                <Space size={4}>
                                    <FileCheck size={14} className="text-blue-500" />
                                    <Text strong style={{ fontSize: '16px' }}>{data?.total_artifact_count || 0}</Text>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>Items</Text>
                                </Space>
                            </div>
                            <div>
                                <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>爆发风险 (Truncated)</Text>
                                <Space size={4}>
                                    <Zap size={14} className={explosionRisk > 0 ? "text-orange-500" : "text-gray-300"} />
                                    <Text strong style={{ fontSize: '16px' }}>{explosionRisk}</Text>
                                    <Text type="secondary" style={{ fontSize: '12px' }}>Runs</Text>
                                    {explosionRisk > 0 && (
                                        <Tooltip title="部分运行产物过多，已触发 10 样本截断策略。建议检查相关测试的生成逻辑。">
                                            <AlertTriangle size={14} className="text-orange-400" />
                                        </Tooltip>
                                    )}
                                </Space>
                            </div>
                        </div>
                    </Col>
                </Row>
            </Space>
        </Card>
    );
};

export default EvidenceCoverageCard;
