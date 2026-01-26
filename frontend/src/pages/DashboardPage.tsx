import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Table, Typography, Statistic, Spin, Alert, Tag } from 'antd';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Zap, TrendingUp, Activity } from 'lucide-react';
import orchestrationsApi, { RunSummary, RunDetail } from '../api/orchestrations';

const { Title, Text } = Typography;

interface DashboardStats {
    passCount: number;
    failCount: number;
    hitlCount: number;
    avgElapsedMs: number | null;
    shortCircuitCount: number;
    totalRuns: number;
}

interface TrendPoint {
    runId: string;
    elapsedMs: number;
    startedAt: string;
}

const DashboardPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [stats, setStats] = useState<DashboardStats>({
        passCount: 0,
        failCount: 0,
        hitlCount: 0,
        avgElapsedMs: null,
        shortCircuitCount: 0,
        totalRuns: 0,
    });
    const [trendData, setTrendData] = useState<TrendPoint[]>([]);
    const [recentRuns, setRecentRuns] = useState<(RunSummary & Partial<RunDetail>)[]>([]);

    useEffect(() => {
        const fetchDashboardData = async () => {
            setLoading(true);
            setError(null);
            try {
                // Fetch runs list
                const runsRes = await orchestrationsApi.listRuns({ limit: 50 });
                const runs = runsRes.runs;

                // Fetch details for top 10 runs (concurrency limit 5)
                const detailPromises: Promise<RunDetail | null>[] = [];
                const top10 = runs.slice(0, 10);

                for (let i = 0; i < top10.length; i += 5) {
                    const batch = top10.slice(i, i + 5);
                    const batchResults = await Promise.all(
                        batch.map(run =>
                            orchestrationsApi.getRunDetail(run.run_id).catch(() => null)
                        )
                    );
                    detailPromises.push(...batchResults.map(r => Promise.resolve(r)));
                }

                const details = await Promise.all(detailPromises);
                const detailMap = new Map<string, RunDetail>();
                details.forEach(d => {
                    if (d) detailMap.set(d.run_id, d);
                });

                // Calculate stats
                let passCount = 0, failCount = 0, hitlCount = 0, shortCircuitCount = 0;
                const elapsedValues: number[] = [];
                const trend: TrendPoint[] = [];

                runs.forEach(run => {
                    const decision = run.decision?.toUpperCase();
                    if (decision === 'PASS' || decision === 'APPROVED') passCount++;
                    else if (decision === 'FAIL' || decision === 'REJECTED') failCount++;
                    else if (decision === 'NEED_HITL' || decision === 'PENDING') hitlCount++;

                    const detail = detailMap.get(run.run_id);
                    if (detail?.governance) {
                        const elapsed = (detail.governance as any).elapsed_ms_total;
                        if (typeof elapsed === 'number') {
                            elapsedValues.push(elapsed);
                            trend.push({
                                runId: run.run_id.slice(0, 8),
                                elapsedMs: elapsed,
                                startedAt: run.started_at,
                            });
                        }
                        if ((detail.governance as any).short_circuited) {
                            shortCircuitCount++;
                        }
                    }
                });

                const avgElapsedMs = elapsedValues.length > 0
                    ? Math.round(elapsedValues.reduce((a, b) => a + b, 0) / elapsedValues.length)
                    : null;

                setStats({
                    passCount,
                    failCount,
                    hitlCount,
                    avgElapsedMs,
                    shortCircuitCount,
                    totalRuns: runs.length,
                });

                setTrendData(trend.slice(0, 20).reverse());

                // Merge details into recent runs
                const merged = runs.slice(0, 10).map(run => ({
                    ...run,
                    ...detailMap.get(run.run_id),
                }));
                setRecentRuns(merged);

            } catch (err: any) {
                if (err.response?.status === 401) {
                    setError('需要登录 (401)');
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
            render: (_: any, record: any) => {
                const version = record.policy?.version;
                const hash = record.policy?.hash?.slice(0, 8);
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
                            value={stats.passCount}
                            prefix={<CheckCircle2 size={20} className="text-green-500" />}
                            valueStyle={{ color: '#52c41a' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="FAIL"
                            value={stats.failCount}
                            prefix={<XCircle size={20} className="text-red-500" />}
                            valueStyle={{ color: '#ff4d4f' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="NEED_HITL"
                            value={stats.hitlCount}
                            prefix={<AlertTriangle size={20} className="text-yellow-500" />}
                            valueStyle={{ color: '#faad14' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} md={6}>
                    <Card>
                        <Statistic
                            title="Avg Elapsed (ms)"
                            value={stats.avgElapsedMs ?? '—'}
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
                            value={stats.shortCircuitCount}
                            prefix={<Zap size={20} className="text-purple-500" />}
                            suffix={`/ ${stats.totalRuns}`}
                        />
                    </Card>
                </Col>
                <Col xs={24} md={16}>
                    <Card title={<><TrendingUp size={16} style={{ marginRight: 8 }} />执行耗时趋势</>}>
                        {trendData.length > 0 ? (
                            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 100 }}>
                                {trendData.map((point, idx) => {
                                    const maxMs = Math.max(...trendData.map(p => p.elapsedMs));
                                    const height = maxMs > 0 ? (point.elapsedMs / maxMs) * 80 : 10;
                                    return (
                                        <div
                                            key={idx}
                                            title={`${point.runId}: ${point.elapsedMs}ms`}
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
                    dataSource={recentRuns}
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
