import React, { useEffect, useState, useMemo } from 'react';
import { Card, Row, Col, Table, Typography, Statistic, Spin, Alert, Tag, Select, Space, Empty } from 'antd';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Zap, TrendingUp, Activity, Filter } from 'lucide-react';
import orchestrationsApi, { DashboardSummaryResponse, DashboardRecentRun, DashboardTrendPoint } from '../api/orchestrations';

const { Title, Text } = Typography;

type DecisionFilter = 'ALL' | 'PASS' | 'FAIL' | 'NEED_HITL';

const DashboardPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<DashboardSummaryResponse | null>(null);

    // 筛选状态
    const [days, setDays] = useState<number>(7);
    const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('ALL');

    useEffect(() => {
        const fetchDashboardData = async () => {
            setLoading(true);
            setError(null);
            try {
                const summary = await orchestrationsApi.getDashboardSummary({ days, limit: 50 });
                setData(summary);
            } catch (err: any) {
                if (err.response?.status === 401) {
                    setError('需要登录才能访问 Dashboard');
                } else if (err.response?.status === 403) {
                    setError('您没有权限访问 Dashboard，请联系管理员');
                } else if (err.response?.status === 500) {
                    setError('服务器内部错误，请稍后重试');
                } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
                    setError('请求超时，请检查网络连接');
                } else {
                    setError(err.message || '加载失败，请刷新页面重试');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [days]);

    // 根据 decision filter 过滤 recent_runs
    const filteredRuns = useMemo(() => {
        if (!data?.recent_runs) return [];
        if (decisionFilter === 'ALL') return data.recent_runs;
        return data.recent_runs.filter(run => {
            const upper = run.decision?.toUpperCase();
            if (decisionFilter === 'PASS') return upper === 'PASS' || upper === 'APPROVED';
            if (decisionFilter === 'FAIL') return upper === 'FAIL' || upper === 'REJECTED';
            if (decisionFilter === 'NEED_HITL') return upper === 'NEED_HITL' || upper === 'PENDING';
            return true;
        });
    }, [data?.recent_runs, decisionFilter]);

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
                <Spin size="large" tip="加载中..." />
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ padding: 24, maxWidth: 600, margin: '0 auto' }} data-testid="dashboard-error">
                <Alert
                    message="加载失败"
                    description={error}
                    type="error"
                    showIcon
                    action={
                        <a onClick={() => window.location.reload()}>刷新页面</a>
                    }
                />
            </div>
        );
    }

    if (!data) {
        return (
            <div style={{ padding: 24 }} data-testid="dashboard-empty">
                <Empty description="暂无数据" />
            </div>
        );
    }

    const { cards, trend } = data;
    const trendData = trend.filter((p: DashboardTrendPoint) => p.elapsed_ms !== null);

    return (
        <div style={{ padding: '24px' }} data-testid="dashboard-summary">
            <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
                <Col>
                    <Title level={2} style={{ margin: 0 }}>
                        <Activity size={24} style={{ marginRight: 12, verticalAlign: 'middle' }} />
                        L5 Dashboard
                    </Title>
                </Col>
                <Col>
                    <Space size="middle">
                        <Space>
                            <Filter size={16} />
                            <Text type="secondary">时间窗口:</Text>
                            <Select
                                value={days}
                                onChange={setDays}
                                style={{ width: 100 }}
                                options={[
                                    { value: 7, label: '7 天' },
                                    { value: 30, label: '30 天' },
                                    { value: 90, label: '90 天' },
                                ]}
                                data-testid="days-filter"
                            />
                        </Space>
                        <Space>
                            <Text type="secondary">决策筛选:</Text>
                            <Select
                                value={decisionFilter}
                                onChange={setDecisionFilter}
                                style={{ width: 120 }}
                                options={[
                                    { value: 'ALL', label: '全部' },
                                    { value: 'PASS', label: 'PASS' },
                                    { value: 'FAIL', label: 'FAIL' },
                                    { value: 'NEED_HITL', label: 'NEED_HITL' },
                                ]}
                                data-testid="decision-filter"
                            />
                        </Space>
                    </Space>
                </Col>
            </Row>

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
                    <Card title={<><TrendingUp size={16} style={{ marginRight: 8 }} />执行耗时趋势 (最近 {days} 天)</>}>
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
                            <Empty description="无趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        )}
                    </Card>
                </Col>
            </Row>

            {/* Timeseries Daily Trend */}
            <Card
                title={<><TrendingUp size={16} style={{ marginRight: 8 }} />每日趋势 (最近 {days} 天)</>}
                style={{ marginBottom: 24 }}
                data-testid="timeseries-section"
            >
                {data.timeseries && data.timeseries.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid #f0f0f0' }}>
                                    <th style={{ padding: '8px 12px', textAlign: 'left' }}>日期</th>
                                    <th style={{ padding: '8px 12px', textAlign: 'center', color: '#52c41a' }}>PASS</th>
                                    <th style={{ padding: '8px 12px', textAlign: 'center', color: '#ff4d4f' }}>FAIL</th>
                                    <th style={{ padding: '8px 12px', textAlign: 'center', color: '#faad14' }}>NEED_HITL</th>
                                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>总计</th>
                                    <th style={{ padding: '8px 12px', textAlign: 'left', minWidth: 200 }}>分布</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.timeseries.map((point, idx) => {
                                    const total = point.total || 1;
                                    const passWidth = (point.pass_count / total) * 100;
                                    const failWidth = (point.fail_count / total) * 100;
                                    const hitlWidth = (point.need_hitl_count / total) * 100;
                                    return (
                                        <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                                            <td style={{ padding: '8px 12px' }}>{point.date}</td>
                                            <td style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 500, color: '#52c41a' }}>{point.pass_count}</td>
                                            <td style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 500, color: '#ff4d4f' }}>{point.fail_count}</td>
                                            <td style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 500, color: '#faad14' }}>{point.need_hitl_count}</td>
                                            <td style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600 }}>{point.total}</td>
                                            <td style={{ padding: '8px 12px' }}>
                                                <div style={{ display: 'flex', height: 16, borderRadius: 4, overflow: 'hidden', background: '#f5f5f5' }}>
                                                    {passWidth > 0 && <div style={{ width: `${passWidth}%`, background: '#52c41a' }} title={`PASS: ${point.pass_count}`} />}
                                                    {failWidth > 0 && <div style={{ width: `${failWidth}%`, background: '#ff4d4f' }} title={`FAIL: ${point.fail_count}`} />}
                                                    {hitlWidth > 0 && <div style={{ width: `${hitlWidth}%`, background: '#faad14' }} title={`NEED_HITL: ${point.need_hitl_count}`} />}
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <Empty description="无每日趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
            </Card>

            {/* Recent Runs Table */}

            <Card
                title={
                    <Space>
                        近期 Runs
                        {decisionFilter !== 'ALL' && (
                            <Tag color="blue">筛选: {decisionFilter}</Tag>
                        )}
                    </Space>
                }
                style={{ marginBottom: 24 }}
            >
                {filteredRuns.length > 0 ? (
                    <Table
                        columns={columns}
                        dataSource={filteredRuns}
                        rowKey="run_id"
                        pagination={false}
                        size="small"
                        data-testid="dashboard-table"
                    />
                ) : (
                    <Empty
                        description={
                            decisionFilter !== 'ALL'
                                ? `没有 ${decisionFilter} 状态的运行记录`
                                : '暂无运行记录'
                        }
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                )}
            </Card>
        </div>
    );
};

export default DashboardPage;
