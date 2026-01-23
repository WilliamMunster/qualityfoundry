import React, { useEffect, useState } from 'react';
import { Typography, Table, Tag, Button, Space, message } from 'antd';
import { PlayCircle, Eye, Clock, Hash, ShieldCheck, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import orchestrationsApi, { RunSummary } from '../api/orchestrations';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const RunListPage: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<RunSummary[]>([]);
    const [total, setTotal] = useState(0);

    const loadData = async (pagination = { current: 1, pageSize: 10 }) => {
        setLoading(true);
        try {
            const res = await orchestrationsApi.listRuns({
                limit: pagination.pageSize,
                offset: (pagination.current - 1) * pagination.pageSize,
            });
            setData(res.runs);
            setTotal(res.total);
        } catch (error) {
            console.error('Failed to load runs:', error);
            message.error('加载运行列表失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const columns = [
        {
            title: '运行 ID',
            dataIndex: 'run_id',
            key: 'run_id',
            render: (id: string) => (
                <Space>
                    <Hash size={14} className="text-gray-400" />
                    <Text copyable={{ text: id }}>
                        <a onClick={() => navigate(`/runs/${id}`)} style={{ fontFamily: 'monospace' }}>
                            {id.substring(0, 8)}...
                        </a>
                    </Text>
                </Space>
            ),
        },
        {
            title: '决策结果',
            dataIndex: 'decision',
            key: 'decision',
            render: (decision: string) => {
                if (!decision) return <Tag color="default">执行中</Tag>;
                const colorMap: Record<string, string> = {
                    PASS: 'success',
                    FAIL: 'error',
                    NEED_HITL: 'warning',
                };
                return <Tag color={colorMap[decision] || 'blue'}>{decision}</Tag>;
            },
        },
        {
            title: '决策来源',
            dataIndex: 'decision_source',
            key: 'decision_source',
            render: (source: string) => source ? <Tag icon={<ShieldCheck size={12} />}>{source}</Tag> : '-',
        },
        {
            title: '工具调用',
            dataIndex: 'tool_count',
            key: 'tool_count',
            render: (count: number) => (
                <Space>
                    <Activity size={14} className="text-gray-400" />
                    <span>{count} 次</span>
                </Space>
            ),
        },
        {
            title: '开始时间',
            dataIndex: 'started_at',
            key: 'started_at',
            render: (time: string) => (
                <Space>
                    <Clock size={14} className="text-gray-400" />
                    <span>{dayjs(time).format('YYYY-MM-DD HH:mm:ss')}</span>
                </Space>
            ),
        },
        {
            title: '操作',
            key: 'action',
            render: (_: any, record: RunSummary) => (
                <Button
                    type="link"
                    icon={<Eye size={16} />}
                    onClick={() => navigate(`/runs/${record.run_id}`)}
                >
                    分析
                </Button>
            ),
        },
    ];

    return (
        <div style={{ padding: '4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <Title level={3} style={{ margin: 0 }}>执行中心</Title>
                <Button
                    type="primary"
                    icon={<PlayCircle size={18} style={{ marginRight: 4 }} />}
                    onClick={() => navigate('/runs/new')}
                    style={{ borderRadius: '24px', height: '40px' }}
                >
                    开启新运行
                </Button>
            </div>

            <Table
                columns={columns}
                dataSource={data}
                rowKey="run_id"
                loading={loading}
                pagination={{
                    total,
                    pageSize: 10,
                    showSizeChanger: true,
                    onChange: (page, pageSize) => loadData({ current: page, pageSize }),
                }}
            />
        </div>
    );
};

export default RunListPage;
