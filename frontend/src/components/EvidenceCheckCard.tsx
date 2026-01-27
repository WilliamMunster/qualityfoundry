import React from 'react';
import { Card, Typography, Space, Tag, Row, Col, Tooltip } from 'antd';
import { ShieldCheck, Info, Binary, HelpCircle, AlertCircle } from 'lucide-react';
import { ArtifactAuditSummary } from '../api/orchestrations';

const { Text, Paragraph } = Typography;

interface Props {
    data: ArtifactAuditSummary | null | undefined;
    runId?: string;
}

const EvidenceCheckCard: React.FC<Props> = ({ data, runId }) => {
    const [playwrightStatus, setPlaywrightStatus] = React.useState<{ status: string; reason: string; skip_code?: string } | null>(null);

    // 标准化诊断映射 (Option 1: User-friendly diagnostics)
    const DIAGNOSTIC_MAP: Record<string, { label: string; action: string; type: 'warning' | 'error' }> = {
        'BROWSER_NOT_INSTALLED': {
            label: '执行环境未检测到浏览器',
            action: '请在 Runner 中运行 `playwright install` 或检查容器 Base Image。',
            type: 'error'
        },
        'PLAYWRIGHT_E2E_DISABLED': {
            label: 'UI 测试功能未开启',
            action: '检查环境变量 `QF_ENABLE_UI_TESTS` 是否设置为 1。',
            type: 'warning'
        },
        'SANDBOX_DENIED': {
            label: '沙箱权限拒绝',
            action: '当前策略禁止执行浏览器相关命令，请联系管理员调整 Governance Policy。',
            type: 'error'
        },
        'POLICY_BLOCKED': {
            label: '执行策略拦截',
            action: '检测到非白名单域名访问，UI 测试已熔断。',
            type: 'warning'
        },
        'UNKNOWN': {
            label: '执行异常 (未知原因)',
            action: '请检查 Standard Error (stderr) 日志获取详细堆栈。',
            type: 'warning'
        }
    };

    React.useEffect(() => {
        if (runId && data) {
            // 在样本中寻找状态快照文件
            const statusSample = data.samples.find(s =>
                (s.rel_path && s.rel_path.endsWith('playwright_status.json')) ||
                (s.path && s.path.endsWith('playwright_status.json'))
            );

            if (statusSample) {
                // 模拟根据样本内容解析的状态。
                // 真实场景下，前端应根据 statusSample 的 preview_url 再次 fetch 文件内容。
                // 此处我们利用之前在 runner 中存入的 skip_code（逻辑模拟）
                setPlaywrightStatus({
                    status: 'skipped',
                    reason: 'Playwright tests were skipped.',
                    skip_code: 'BROWSER_NOT_INSTALLED' // 模拟从内容中解析的结果
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
                {/* P1: Playwright Skip Alert / Diagnostics */}
                {playwrightStatus && (
                    <div style={{
                        padding: '12px',
                        background: playwrightStatus.skip_code ? (DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.type === 'error' ? '#fff1f0' : '#fff7e6') : '#fff7e6',
                        borderRadius: 12,
                        border: '1px solid',
                        borderColor: playwrightStatus.skip_code ? (DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.type === 'error' ? '#ffa39e' : '#ffe7ba') : '#ffe7ba'
                    }}>
                        <Space align="start">
                            {playwrightStatus.skip_code && DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.type === 'error'
                                ? <AlertCircle size={16} className="text-red-500" style={{ marginTop: 2 }} />
                                : <HelpCircle size={16} className="text-orange-500" style={{ marginTop: 2 }} />
                            }
                            <div>
                                <Text strong style={{ fontSize: '13px', color: playwrightStatus.skip_code && DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.type === 'error' ? '#cf1322' : '#d46b08' }}>
                                    {playwrightStatus.skip_code ? DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.label : 'UI 测试已跳过'}
                                </Text>
                                <br />
                                {playwrightStatus.skip_code ? (
                                    <Paragraph type="secondary" style={{ fontSize: '12px', margin: '4px 0 0 0' }}>
                                        <Text strong>建议操作：</Text> {DIAGNOSTIC_MAP[playwrightStatus.skip_code]?.action}
                                    </Paragraph>
                                ) : (
                                    <Text style={{ fontSize: '12px', color: '#8c8c8c' }}>{playwrightStatus.reason}</Text>
                                )}
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
