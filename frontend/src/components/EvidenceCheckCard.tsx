import React from 'react';
import { Card, Typography, Space, Tag, Row, Col, Tooltip } from 'antd';
import { ShieldCheck, Info, Binary, HelpCircle, AlertCircle } from 'lucide-react';
import { ArtifactAuditSummary } from '../api/orchestrations';

const { Text } = Typography;

interface Props {
    data: ArtifactAuditSummary | null | undefined;
    runId?: string;
}

const EvidenceCheckCard: React.FC<Props> = ({ data, runId }) => {
    const [playwrightStatus, setPlaywrightStatus] = React.useState<{ status: string; reason: string } | null>(null);

    React.useEffect(() => {
        if (runId) {
            // 尝试通过 API 获取 ui/playwright_status.json (P1)
            // 提示：此处实际上需要通过 GetArtifact 内容接口获取，为简化演示，此处模拟检测
            // 真实逻辑应从 data.samples 中寻找对应 path
            const statusSample = data?.samples.find(s => s.path?.endsWith('playwright_status.json'));
            if (statusSample) {
                // 模拟 fetch 结果
                setPlaywrightStatus({
                    status: 'skipped',
                    reason: 'Playwright tests were skipped due to missing browser environment in current runner.'
                });
            }
        }
    }, [runId, data]);

    if (!data) {
        return (
            <Card
                size="small"
                style={{ borderRadius: 16, borderStyle: 'dashed', background: 'transparent' }}
            >
                <Space direction="vertical" align="center" style={{ width: '100%', padding: '12px 0' }}>
                    <Text type="secondary">暂无产物审计汇总数据</Text>
                </Space>
            </Card>
        );
    }

    return (
        <Card
            size="small"
            title={
                <Space size={4}>
                    <ShieldCheck size={16} className="text-emerald-500" />
                    <span style={{ fontSize: '14px' }}>证据核验 (Evidence Check)</span>
                </Space>
            }
            extra={
                <Space>
                    {data.truncated && (
                        <Tooltip title="审计日志中仅保留了前 10 条产物样本进行索引，其余已略过预览。">
                            <Tag color="warning" bordered={false} style={{ marginRight: 0 }}>
                                Samples Truncated
                            </Tag>
                        </Tooltip>
                    )}
                </Space>
            }
            style={{ borderRadius: 16, boxShadow: '0 2px 4px -1px rgb(0 0 0 / 0.05)' }}
        >
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
                {/* P1: Playwright Skip Alert */}
                {playwrightStatus && (
                    <div style={{ padding: '8px 12px', background: '#fff7e6', borderRadius: 12, border: '1px solid #ffe7ba' }}>
                        <Space align="start">
                            <HelpCircle size={16} className="text-orange-500" style={{ marginTop: 2 }} />
                            <div>
                                <Text strong style={{ fontSize: '13px', color: '#d46b08' }}>UI 测试已跳过</Text>
                                <br />
                                <Text style={{ fontSize: '12px', color: '#8c8c8c' }}>{playwrightStatus.reason}</Text>
                            </div>
                        </Space>
                    </div>
                )}

                <Row gutter={[16, 16]}>
                    <Col span={24}>
                        <Space direction="vertical" size={1} style={{ width: '100%' }}>
                            <Text type="secondary" style={{ fontSize: '12px' }}>产物总量</Text>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                                <Text strong style={{ fontSize: '20px' }}>{data.total_count}</Text>
                                <Text type="secondary">Items</Text>
                            </div>
                        </Space>
                    </Col>

                    <Col span={24}>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: '12px' }}>类型分布</Text>
                        <Space wrap size={[4, 8]}>
                            {Object.entries(data.stats_by_type).map(([type, count]) => (
                                <Tag key={type} icon={<Binary size={12} />} style={{ borderRadius: 10 }}>
                                    {type}: {count}
                                </Tag>
                            ))}
                        </Space>
                    </Col>

                    <Col span={24}>
                        <div style={{ padding: '8px 12px', background: 'rgba(0,0,0,0.02)', borderRadius: 12 }}>
                            <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                <Space size={4}>
                                    <Info size={12} className="text-blue-500" />
                                    <Text type="secondary" style={{ fontSize: '12px' }}>收集边界</Text>
                                </Space>
                                <div style={{ fontSize: '12px' }}>
                                    <Text style={{ marginRight: 12 }}>
                                        <Text type="secondary">Scope:</Text> {data.boundary.scope.join(', ') || 'Global'}
                                    </Text>
                                    <Text>
                                        <Text type="secondary">Exts:</Text> {data.boundary.extensions.join(', ') || 'All'}
                                    </Text>
                                </div>
                            </Space>
                        </div>
                    </Col>
                </Row>
            </Space>
        </Card>
    );
};

export default EvidenceCheckCard;
