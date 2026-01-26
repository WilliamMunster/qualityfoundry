import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Table, Typography, Statistic, Spin, Alert, Tag } from 'antd';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Zap, TrendingUp, Activity } from 'lucide-react';
import orchestrationsApi, { DashboardSummaryResponse, DashboardRecentRun, DashboardTrendPoint } from '../api/orchestrations';

const { Title, Text } = Typography;

const DashboardPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<DashboardSummaryResponse | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            setLoading(true);
            setError(null);
            try {
                // 单次 API 调用获取所有 Dashboard 数据
                const summary = await orchestrationsApi.getDashboardSummary(50);
                setData(summary);
            } catch (err: any) {
                if (err.response?.status === 401) {
                    setError('需要登录 (401)');
                } else if (err.response?.status === 403) {
                    setError('无权限访问 (403)');
                } else {
                    setError(err.message || '加载失败');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    const columns = [
        {
            title: 'Run ID',
            dataIndex: 'run_id',
            key: 'run_id',
            render: (id: string) => <Text code>{id?.slice(0, 8)}...</Text>,
        },
        {
            title: '开始时间',
            dataIndex: 'started_at',
            key: 'started_at',
            render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '—',
        },
        {
            title: '决策',
            dataIndex: 'decision',
            key: 'decision',
            render: (d: string) => {
                if (!d) return '—';
                const upper = d.toUpperCase();
                if (upper === 'PASS' || upper === 'APPROVED') return <Tag color="success">{d}</Tag>;
                if (upper === 'FAIL' || upper === 'REJECTED') return <Tag color="error">{d}</Tag>;
                return <Tag color="warning">{d}</Tag>;
            },
        },
        {
            title: 'Policy',
            key: 'policy',
            render: (_: any, record: DashboardRecentRun) => {
                const version = record.policy_version;
                const hash = record.policy_hash;
                if (version || hash) return <Text type="secondary">{version || hash}</Text>;
                return '—';
            },
        },
        {
            title: 'Tools',
            dataIndex: 'tool_count',
            key: 'tool_count',
            render: (c: number) => c ?? '—',
        },
    ];

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
                <Spin size="large" />
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ padding: 24 }} data-testid="dashboard-error">
                <Alert message={error} type="warning" showIcon />
            </div>
        );
    }

    if (!data) {
        return (
            <div style={{ padding: 24 }} data-testid="dashboard-error">
                <Alert message="无数据" type="info" showIcon />
            </div>
        );
    }

    const { cards, trend, recent_runs } = data;

    // 转换 trend 数据用于渲染
    const trendData = trend.filter((p: DashboardTrendPoint) => p.elapsed_ms !== null);

    return (
        <div style={{ padding: '24px' }} data-testid="dashboard-summary">
            <Title level={2} style={{ marginBottom: 24 }}>
                <Activity size={24} style={{ marginRight: 12, verticalAlign: 'middle' }} />
                L5 Dashboard
            </Title>

            {/* Summary Cards */}
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="PASS"
                            value={cards.pass_count}
                            prefix={<CheckCircle2 size={20} className="text-green-500" />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="FAIL"
                            value={cards.fail_count}
                            prefix={<XCircle size={20} className="text-red-500" />}
                            valueStyle={{ color: '#ff4d4f' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="NEED_HITL"
                            value={cards.hitl_count}
                            prefix={<AlertTriangle size={20} className="text-yellow-500" />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="Avg Elapsed (ms)"
                            value={cards.avg_elapsed_ms !== null ? Math.round(cards.avg_elapsed_ms) : '—'}
                            prefix={<Clock size={20} className="text-blue-500" />}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Short Circuit & Trend */}
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
                <Col xs={24} md={8}>
                    <Card>
                        <Statistic
                            title="Short Circuit 次数"
                            value={cards.short_circuit_count}
                            prefix={<Zap size={20} className="text-purple-500" />}
                            suffix={`/ ${cards.total_runs}`}
                        />
                    </Card>
                </Col>
                <Col xs={24} md={16}>
                    <Card title={<><TrendingUp size={16} style={{ marginRight: 8 }} />执行耗时趋势</>}>
                        {trendData.length > 0 ? (
                            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 100 }}>
                                {trendData.map((point: DashboardTrendPoint, idx: number) => {
                                    const maxMs = Math.max(...trendData.map((p: DashboardTrendPoint) => p.elapsed_ms || 0));
                                    const height = maxMs > 0 ? ((point.elapsed_ms || 0) / maxMs) * 80 : 10;
                                    return (
                                        <div
                                            key={idx}
                                            title={`${point.run_id}: ${point.elapsed_ms}ms`}
                                            style={{
                                                flex: 1,
                                                height: height + 10,
                                                background: 'linear-gradient(180deg, #1890ff 0%, #69c0ff 100%)',
                                                borderRadius: 4,
                                                minWidth: 8,
                                            }}
                                        />
                                    );
                                })}
                            </div>
                        ) : (
                            <Text type="secondary">无数据</Text>
                        )}
                    </Card>
                </Col>
            </Row>

            {/* Recent Runs Table */}
            <Card title="近期 Runs" style={{ marginBottom: 24 }}>
                <Table
                    columns={columns}
                    dataSource={recent_runs}
                    rowKey="run_id"
                    pagination={false}
                    size="small"
                    data-testid="dashboard-table"
                />
            </Card>
        </div>
    );
};

export default DashboardPage;
