import { Tabs, Descriptions, Tag, List, Card, Typography, Space, Image } from 'antd';
import {
    Info,
    ShieldCheck,
    RefreshCcw,
    ScrollText,
    Wrench,
    FolderOpen,
    CheckCircle2,
    FileText,
    Download,
    Eye
} from 'lucide-react';

const { Text, Title, Paragraph } = Typography;

interface EvidenceSplitterProps {
    evidence: any;
    runId: string;
}

const EvidenceSplitter: React.FC<EvidenceSplitterProps> = ({ evidence, runId }) => {
    if (!evidence) return null;

    const isImage = (path: string) => {
        const ext = path.split('.').pop()?.toLowerCase();
        return ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext || '');
    };

    const items = [
        {
            key: 'summary',
            label: <Space><Info size={16} />概要</Space>,
            children: (
                <Descriptions bordered column={1}>
                    <Descriptions.Item label="运行 ID">{runId}</Descriptions.Item>
                    <Descriptions.Item label="输入描述">{evidence.input_nl || '-'}</Descriptions.Item>
                    <Descriptions.Item label="决策结论">
                        <Tag color={evidence.decision === 'PASS' ? 'success' : 'error'}>{evidence.decision}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="决策原因">{evidence.reason || '-'}</Descriptions.Item>
                </Descriptions>
            )
        },
        {
            key: 'governance',
            label: <Space><ShieldCheck size={16} />治理</Space>,
            children: (
                <Card title="质量门禁结果" variant="outlined">
                    <Text strong>决策来源：</Text> <Tag>{evidence.decision_source || 'AI_JUDGE'}</Tag>
                    <div style={{ marginTop: 16 }}>
                        <Text type="secondary">基于 Policy Hash: </Text>
                        <code>{evidence.policy_hash || 'Current'}</code>
                    </div>
                </Card>
            )
        },
        {
            key: 'repro',
            label: <Space><RefreshCcw size={16} />可复现性</Space>,
            children: (
                <Descriptions bordered column={2}>
                    <Descriptions.Item label="Git SHA"><code>{evidence.repro?.git_sha?.substring(0, 8) || 'unknown'}</code></Descriptions.Item>
                    <Descriptions.Item label="分支">{evidence.repro?.git_branch || '-'}</Descriptions.Item>
                    <Descriptions.Item label="环境 ID">{evidence.environment?.environment_id || '-'}</Descriptions.Item>
                    <Descriptions.Item label="依赖指纹"><code>{evidence.repro?.dependency_fingerprint?.substring(0, 16) || '-'}</code>... </Descriptions.Item>
                </Descriptions>
            )
        },
        {
            key: 'policy',
            label: <Space><ScrollText size={16} />策略 (只读)</Space>,
            children: (
                <Card variant="borderless" style={{ background: '#f5f5f5', borderRadius: 8 }}>
                    <pre style={{ margin: 0, fontSize: '12px' }}>
                        {JSON.stringify(evidence.policy_snapshot || { info: "Policy snapshot in evidence.json not found" }, null, 2)}
                    </pre>
                </Card>
            )
        },
        {
            key: 'tool_calls',
            label: <Space><Wrench size={16} />工具调用</Space>,
            children: (
                <List
                    itemLayout="horizontal"
                    dataSource={evidence.tool_results || []}
                    renderItem={(item: any) => (
                        <List.Item>
                            <Card style={{ width: '100%' }} size="small" title={`Tool: ${item.tool_name}`}>
                                <Space direction="vertical" style={{ width: '100%' }}>
                                    <Tag color={item.result?.status === 'SUCCESS' ? 'success' : 'error'}>{item.result?.status}</Tag>
                                    {item.result?.stdout && (
                                        <div style={{ background: '#2d2d2d', color: '#ccc', padding: 8, borderRadius: 4, maxHeight: 200, overflow: 'auto' }}>
                                            <pre style={{ margin: 0, fontSize: '11px' }}>{item.result.stdout}</pre>
                                        </div>
                                    )}
                                </Space>
                            </Card>
                        </List.Item>
                    )}
                />
            )
        },
        {
            key: 'artifacts',
            label: <Space><FolderOpen size={16} />产物</Space>,
            children: (
                <List
                    grid={{ gutter: 16, xs: 1, sm: 2, md: 3 }}
                    dataSource={evidence.artifacts || []}
                    renderItem={(path: string) => {
                        const url = `/api/v1/artifacts/${runId}/${path}`;
                        const isImg = isImage(path);
                        return (
                            <List.Item>
                                <Card
                                    hoverable
                                    size="small"
                                    cover={isImg ? (
                                        <div style={{ height: 120, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
                                            <Image
                                                src={url}
                                                alt={path}
                                                style={{ maxHeight: 120, objectFit: 'contain' }}
                                                preview={{ mask: <Space><Eye size={14} />预览</Space> }}
                                            />
                                        </div>
                                    ) : (
                                        <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f1f5f9' }}>
                                            <FileText size={48} className="text-slate-300" />
                                        </div>
                                    )}
                                    actions={[
                                        <a href={url} target="_blank" rel="noreferrer" key="download">
                                            <Space><Download size={14} />下载</Space>
                                        </a>
                                    ]}
                                >
                                    <Card.Meta
                                        title={<Text style={{ fontSize: 12 }} ellipsis={{ tooltip: path }}>{path}</Text>}
                                    />
                                </Card>
                            </List.Item>
                        );
                    }}
                />
            )
        },
        {
            key: 'decision',
            label: <Space><CheckCircle2 size={16} />最终决策</Space>,
            children: (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Title level={2} style={{ color: evidence.decision === 'PASS' ? '#10B981' : '#EF4444' }}>
                        {evidence.decision}
                    </Title>
                    <Paragraph type="secondary" style={{ maxWidth: 600, margin: '24px auto' }}>
                        {evidence.reason}
                    </Paragraph>
                </div>
            )
        }
    ];

    return (
        <Tabs defaultActiveKey="summary" items={items} />
    );
};

export default EvidenceSplitter;
