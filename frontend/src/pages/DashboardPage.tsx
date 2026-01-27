import React, { useEffect, useState, useMemo } from 'react';
import { Card, Row, Col, Table, Typography, Statistic, Spin, Alert, Tag, Select, Space, Empty, Button, Collapse } from 'antd';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Zap, TrendingUp, Activity, Filter, GitCompare, Shield, AlertCircle } from 'lucide-react';
import orchestrationsApi, { DashboardSummaryResponse, DashboardRecentRun, DashboardTrendPoint, PolicyInfo } from '../api/orchestrations';
import EvidenceCoverageCard from '../components/Dashboard/EvidenceCoverageCard';

const { Title, Text } = Typography;

type DecisionFilter = 'ALL' | 'PASS' | 'FAIL' | 'NEED_HITL';

const DashboardPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<DashboardSummaryResponse | null>(null);

    // 筛选状态
    const [days, setDays] = useState<number>(7);
    const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>('ALL');
    const [policyHashFilter, setPolicyHashFilter] = useState<string | null>(null);

    // Policy Diff 状态
    const [policyHashA, setPolicyHashA] = useState<string | null>(null);
    const [policyHashB, setPolicyHashB] = useState<string | null>(null);
    const [showDiff, setShowDiff] = useState(false);

    // P2-2: 当前策略信息
    const [currentPolicy, setCurrentPolicy] = useState<PolicyInfo | null>(null);

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

    // P2-2: 获取当前策略信息
    useEffect(() => {
        orchestrationsApi.getCurrentPolicy()
            .then(setCurrentPolicy)
            .catch(() => setCurrentPolicy(null));
    }, []);

    // Policy hash 选项
    const policyHashOptions = useMemo(() => {
        if (!data?.by_policy_hash) return [];
        return Object.keys(data.by_policy_hash).map(hash => ({
            value: hash,
            label: `${hash} (${data.by_policy_hash[hash]} runs)`,
        }));
    }, [data?.by_policy_hash]);

    // 根据 decision/policy filter 过滤 recent_runs
    const filteredRuns = useMemo(() => {
        if (!data?.recent_runs) return [];
        let runs = data.recent_runs;

        // Policy hash filter
        if (policyHashFilter) {
            runs = runs.filter(run => run.policy_hash === policyHashFilter);
        }

        // Decision filter
        if (decisionFilter !== 'ALL') {
            runs = runs.filter(run => {
                const upper = run.decision?.toUpperCase();
                if (decisionFilter === 'PASS') return upper === 'PASS' || upper === 'APPROVED';
                if (decisionFilter === 'FAIL') return upper === 'FAIL' || upper === 'REJECTED';
                if (decisionFilter === 'NEED_HITL') return upper === 'NEED_HITL' || upper === 'PENDING';
                return true;
            });
        }

        return runs;
    }, [data?.recent_runs, decisionFilter, policyHashFilter]);

    // Diff 对比逻辑
    const diffResult = useMemo(() => {
        if (!showDiff || !policyHashA || !policyHashB || !data?.by_policy_hash) return null;
        const countA = data.by_policy_hash[policyHashA] || 0;
        const countB = data.by_policy_hash[policyHashB] || 0;
        const diff = countA - countB;
        return { countA, countB, diff };
    }, [showDiff, policyHashA, policyHashB, data?.by_policy_hash]);

    // 应用 hash 过滤并重置 diff 视图
    const applyHashFilter = (hash: string) => {
        setPolicyHashFilter(hash);
        setShowDiff(false);
    };

    // 清除 hash 过滤
    const clearHashFilter = () => {
        setPolicyHashFilter(null);
    };

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

            {/* P1: Evidence Coverage Section */}
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
                <Col xs={24}>
                    <EvidenceCoverageCard
                        data={data.cards.artifact_metrics}
                        totalRuns={data.cards.total_runs}
                        loading={loading}
                    />
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

            {/* Timeseries Daily Trend - Enhanced P2-3 */}
            <Card
                title={<><TrendingUp size={16} style={{ marginRight: 8 }} />每日趋势 (最近 {days} 天)</>}
                style={{ marginBottom: 24 }}
                data-testid="timeseries-section"
                extra={
                    data.timeseries && data.timeseries.length > 0 && (
                        <Button
                            size="small"
                            onClick={() => {
                                const header = 'Date,Pass,Fail,NeedHITL,Total';
                                const rows = data.timeseries.map(p =>
                                    `${p.date},${p.pass_count},${p.fail_count},${p.need_hitl_count},${p.total}`
                                );
                                const csv = [header, ...rows].join('\n');
                                const blob = new Blob([csv], { type: 'text/csv' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `trend_${days}d_${new Date().toISOString().split('T')[0]}.csv`;
                                a.click();
                                URL.revokeObjectURL(url);
                            }}
                            data-testid="export-csv-btn"
                        >
                            导出 CSV
                        </Button>
                    )
                }
            >
                {data.timeseries && data.timeseries.length > 0 ? (
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                        {/* SVG Line Chart */}
                        {(() => {
                            const ts = data.timeseries;
                            const chartWidth = 600;
                            const chartHeight = 120;
                            const padding = { top: 10, right: 40, bottom: 20, left: 40 };
                            const innerWidth = chartWidth - padding.left - padding.right;
                            const innerHeight = chartHeight - padding.top - padding.bottom;

                            const maxTotal = Math.max(...ts.map(p => p.total), 1);
                            const xStep = ts.length > 1 ? innerWidth / (ts.length - 1) : innerWidth;

                            // 计算 7 日滚动均值和异常点
                            const avgWindow = 7;
                            const anomalyThreshold = 2; // 2x 偏离
                            const anomalies: number[] = [];

                            ts.forEach((point, idx) => {
                                const windowStart = Math.max(0, idx - avgWindow + 1);
                                const windowData = ts.slice(windowStart, idx + 1);
                                const avg = windowData.reduce((s, p) => s + p.total, 0) / windowData.length;
                                if (windowData.length >= 3 && point.total > avg * anomalyThreshold) {
                                    anomalies.push(idx);
                                }
                            });

                            // 生成路径
                            const totalPath = ts.map((p, i) => {
                                const x = padding.left + i * xStep;
                                const y = padding.top + innerHeight - (p.total / maxTotal) * innerHeight;
                                return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                            }).join(' ');

                            const failHitlPath = ts.map((p, i) => {
                                const x = padding.left + i * xStep;
                                const failHitl = p.fail_count + p.need_hitl_count;
                                const y = padding.top + innerHeight - (failHitl / maxTotal) * innerHeight;
                                return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
                            }).join(' ');

                            return (
                                <div style={{ overflowX: 'auto' }}>
                                    <svg width={chartWidth} height={chartHeight} style={{ display: 'block' }}>
                                        {/* Grid lines */}
                                        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={chartHeight - padding.bottom} stroke="#e8e8e8" />
                                        <line x1={padding.left} y1={chartHeight - padding.bottom} x2={chartWidth - padding.right} y2={chartHeight - padding.bottom} stroke="#e8e8e8" />

                                        {/* Total line (blue) */}
                                        <path d={totalPath} fill="none" stroke="#1890ff" strokeWidth={2} />

                                        {/* Fail+HITL line (red) */}
                                        <path d={failHitlPath} fill="none" stroke="#ff4d4f" strokeWidth={2} strokeDasharray="4,2" />

                                        {/* Data points */}
                                        {ts.map((p, i) => {
                                            const x = padding.left + i * xStep;
                                            const y = padding.top + innerHeight - (p.total / maxTotal) * innerHeight;
                                            const isAnomaly = anomalies.includes(i);
                                            return (
                                                <g key={i}>
                                                    <circle cx={x} cy={y} r={4} fill={isAnomaly ? '#faad14' : '#1890ff'} stroke="#fff" strokeWidth={1}>
                                                        <title>{`${p.date}\nTotal: ${p.total}\nPass: ${p.pass_count}\nFail: ${p.fail_count}\nHITL: ${p.need_hitl_count}${isAnomaly ? '\n⚠️ 异常峰值' : ''}`}</title>
                                                    </circle>
                                                    {isAnomaly && (
                                                        <text x={x} y={y - 10} textAnchor="middle" fontSize={10} fill="#faad14">⚠️</text>
                                                    )}
                                                </g>
                                            );
                                        })}

                                        {/* Legend */}
                                        <g transform={`translate(${chartWidth - padding.right + 5}, ${padding.top})`}>
                                            <line x1={0} y1={5} x2={20} y2={5} stroke="#1890ff" strokeWidth={2} />
                                            <text x={25} y={8} fontSize={10} fill="#666">Total</text>
                                            <line x1={0} y1={20} x2={20} y2={20} stroke="#ff4d4f" strokeWidth={2} strokeDasharray="4,2" />
                                            <text x={25} y={23} fontSize={10} fill="#666">Fail+HITL</text>
                                        </g>

                                        {/* Y-axis labels */}
                                        <text x={padding.left - 5} y={padding.top + 4} textAnchor="end" fontSize={10} fill="#999">{maxTotal}</text>
                                        <text x={padding.left - 5} y={chartHeight - padding.bottom} textAnchor="end" fontSize={10} fill="#999">0</text>
                                    </svg>
                                </div>
                            );
                        })()}

                        {/* Table */}
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
                    </Space>
                ) : (
                    <Empty description="无每日趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
            </Card>

            {/* Policy Diff Section - Enhanced P2-2 */}
            <Card
                title={<><GitCompare size={16} style={{ marginRight: 8 }} />Policy 对比</>}
                style={{ marginBottom: 24 }}
                data-testid="policy-diff-section"
            >
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    {/* P2-2: Current Policy Risk Card */}
                    {currentPolicy && (
                        <div style={{ padding: 16, background: '#f6ffed', borderRadius: 8, border: '1px solid #b7eb8f' }} data-testid="policy-risk-card">
                            <Row gutter={16} align="middle">
                                <Col>
                                    <Shield size={20} style={{ color: '#52c41a' }} />
                                </Col>
                                <Col flex="auto">
                                    <Text strong>当前策略</Text>
                                    <Text type="secondary" style={{ marginLeft: 12 }}>
                                        Hash: <Text code>{currentPolicy.policy_hash}</Text>
                                        {currentPolicy.version && <> | v{currentPolicy.version}</>}
                                    </Text>
                                </Col>
                            </Row>

                            {/* Domain-grouped summary */}
                            <Collapse ghost size="small" style={{ marginTop: 12 }}>
                                <Collapse.Panel
                                    header={<Text type="secondary">域配置摘要</Text>}
                                    key="domains"
                                >
                                    <Row gutter={[16, 8]}>
                                        <Col span={12}>
                                            <Space>
                                                <Text type="secondary">🔧 Tools:</Text>
                                                {currentPolicy.summary.tools_allowlist_count === 0 ? (
                                                    <Tag color="orange">允许所有</Tag>
                                                ) : (
                                                    <Tag color="green">{currentPolicy.summary.tools_allowlist_count} 个白名单</Tag>
                                                )}
                                            </Space>
                                        </Col>
                                        <Col span={12}>
                                            <Space>
                                                <Text type="secondary">⏱️ Budget:</Text>
                                                <Tag>超时 {currentPolicy.summary.cost_governance.timeout_s}s</Tag>
                                                <Tag>重试 {currentPolicy.summary.cost_governance.max_retries}</Tag>
                                            </Space>
                                        </Col>
                                        <Col span={12}>
                                            <Space>
                                                <Text type="secondary">🚨 高危关键词:</Text>
                                                <Tag color={currentPolicy.summary.high_risk_keywords_count > 0 ? 'blue' : 'default'}>
                                                    {currentPolicy.summary.high_risk_keywords_count} 个
                                                </Tag>
                                            </Space>
                                        </Col>
                                        <Col span={12}>
                                            <Space>
                                                <Text type="secondary">📝 高危模式:</Text>
                                                <Tag color={currentPolicy.summary.high_risk_patterns_count > 0 ? 'blue' : 'default'}>
                                                    {currentPolicy.summary.high_risk_patterns_count} 个
                                                </Tag>
                                            </Space>
                                        </Col>
                                    </Row>

                                    {/* Security Alerts */}
                                    {currentPolicy.summary.tools_allowlist_count === 0 && (
                                        <Alert
                                            message="工具白名单为空，允许所有工具执行"
                                            type="warning"
                                            showIcon
                                            icon={<AlertCircle size={14} />}
                                            style={{ marginTop: 12 }}
                                        />
                                    )}
                                </Collapse.Panel>
                            </Collapse>
                        </div>
                    )}

                    {/* Hash Comparison */}
                    {policyHashOptions.length >= 2 ? (
                        <>
                            <Row gutter={16} align="middle">
                                <Col>
                                    <Space>
                                        <Text type="secondary">Hash A:</Text>
                                        <Select
                                            value={policyHashA}
                                            onChange={(v) => { setPolicyHashA(v); setShowDiff(false); }}
                                            style={{ width: 200 }}
                                            placeholder="选择 Policy Hash"
                                            options={policyHashOptions}
                                            allowClear
                                            data-testid="policy-hash-a"
                                        />
                                    </Space>
                                </Col>
                                <Col>
                                    <Space>
                                        <Text type="secondary">Hash B:</Text>
                                        <Select
                                            value={policyHashB}
                                            onChange={(v) => { setPolicyHashB(v); setShowDiff(false); }}
                                            style={{ width: 200 }}
                                            placeholder="选择 Policy Hash"
                                            options={policyHashOptions}
                                            allowClear
                                            data-testid="policy-hash-b"
                                        />
                                    </Space>
                                </Col>
                                <Col>
                                    <Button
                                        type="primary"
                                        onClick={() => setShowDiff(true)}
                                        disabled={!policyHashA || !policyHashB || policyHashA === policyHashB}
                                        data-testid="compare-btn"
                                    >
                                        Compare
                                    </Button>
                                </Col>
                            </Row>

                            {/* 错误态：相同 hash */}
                            {policyHashA && policyHashB && policyHashA === policyHashB && (
                                <Alert
                                    message="请选择不同的 Policy Hash 进行对比"
                                    type="warning"
                                    showIcon
                                />
                            )}

                            {/* Diff 结果 */}
                            {diffResult && (
                                <div style={{ padding: 16, background: '#fafafa', borderRadius: 8 }}>
                                    <Row gutter={24}>
                                        <Col span={8}>
                                            <Statistic
                                                title={<><Tag color="blue">{policyHashA}</Tag> Runs</>}
                                                value={diffResult.countA}
                                            />
                                            <Button
                                                size="small"
                                                style={{ marginTop: 8 }}
                                                onClick={() => applyHashFilter(policyHashA!)}
                                                data-testid="apply-filter-a"
                                            >
                                                筛选 Hash A
                                            </Button>
                                        </Col>
                                        <Col span={8}>
                                            <Statistic
                                                title={<><Tag color="green">{policyHashB}</Tag> Runs</>}
                                                value={diffResult.countB}
                                            />
                                            <Button
                                                size="small"
                                                style={{ marginTop: 8 }}
                                                onClick={() => applyHashFilter(policyHashB!)}
                                                data-testid="apply-filter-b"
                                            >
                                                筛选 Hash B
                                            </Button>
                                        </Col>
                                        <Col span={8}>
                                            <Statistic
                                                title="差异"
                                                value={diffResult.diff}
                                                prefix={diffResult.diff > 0 ? '+' : ''}
                                                valueStyle={{ color: diffResult.diff > 0 ? '#52c41a' : diffResult.diff < 0 ? '#ff4d4f' : '#8c8c8c' }}
                                            />
                                        </Col>
                                    </Row>
                                </div>
                            )}
                        </>
                    ) : policyHashOptions.length === 1 ? (
                        <Empty description="只有 1 个 Policy Hash，无法对比" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : !currentPolicy ? (
                        <Empty description="无 Policy Hash 数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : null}
                </Space>
            </Card>

            {/* Recent Runs Table */}

            <Card
                title={
                    <Space>
                        近期 Runs
                        {decisionFilter !== 'ALL' && (
                            <Tag color="blue">决策: {decisionFilter}</Tag>
                        )}
                        {policyHashFilter && (
                            <Tag color="purple" closable onClose={clearHashFilter}>
                                Policy: {policyHashFilter}
                            </Tag>
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
