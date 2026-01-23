import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Row, Col, Typography, Table, Tag, Button, Space, Skeleton } from "antd";
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  ArrowUpRight,
  TrendingUp,
  History,
  Eye
} from "lucide-react";
import apiClient from "../api/client";
import { motion } from "framer-motion";

const { Title, Text } = Typography;

interface Execution {
  id: string;
  testcase_id: string;
  status: string;
  mode: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

const ReportDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failed: 0,
    running: 0,
  });
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [statsData, execData]: [any, any] = await Promise.all([
          apiClient.get("/api/v1/reports/dashboard-stats"),
          apiClient.get("/api/v1/executions", {
            params: { page: 1, page_size: 10 },
          }),
        ]);
        setStats(statsData);
        setRecentExecutions(execData.items || []);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const statCards = [
    { title: '总执行次数', value: stats.total, icon: <History className="text-indigo-500" />, color: '#6366F1' },
    { title: '成功数量', value: stats.success, icon: <CheckCircle className="text-emerald-500" />, color: '#10B981' },
    { title: '失败数量', value: stats.failed, icon: <XCircle className="text-rose-500" />, color: '#EF4444' },
    { title: '正在运行', value: stats.running, icon: <Activity className="text-amber-500" />, color: '#F59E0B' },
  ];

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      render: (id: string) => <Text style={{ fontFamily: 'monospace' }}>{id.substring(0, 8)}...</Text>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (status: string) => {
        const colors: Record<string, string> = {
          success: 'success',
          failed: 'error',
          running: 'processing',
        };
        return <Tag color={colors[status] || 'default'} bordered={false}>{status.toUpperCase()}</Tag>;
      },
    },
    {
      title: "模式",
      dataIndex: "mode",
      key: "mode",
      render: (mode: string) => <Tag bordered={false}>{mode?.toUpperCase()}</Tag>,
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: "分析",
      key: "action",
      render: (_: any, record: Execution) => (
        <Button
          type="link"
          icon={<ArrowUpRight size={16} />}
          onClick={() => navigate(`/runs/${record.id}`)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: '8px' }}>
      <div style={{ marginBottom: 32 }}>
        <Title level={3} style={{ margin: 0 }}>数据驾驶舱</Title>
        <Text type="secondary">实时监测平台质量指标与运行动态</Text>
      </div>

      <Row gutter={[16, 16]}>
        {statCards.map((card, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card variant="outlined" style={{ borderRadius: 16, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Space direction="vertical" size={0}>
                    <Text type="secondary" style={{ fontSize: 13 }}>{card.title}</Text>
                    <Title level={2} style={{ margin: 0 }}>{card.value}</Title>
                  </Space>
                  <div style={{ padding: 10, borderRadius: 12, background: `${card.color}10` }}>
                    {card.icon}
                  </div>
                </div>
                <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <TrendingUp size={14} className="text-emerald-500" />
                  <Text type="secondary" style={{ fontSize: 12 }}>比上周增长 12%</Text>
                </div>
              </Card>
            </motion.div>
          </Col>
        ))}
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={24}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card
              title={<Space><Activity size={18} className="text-indigo-500" />最近执行</Space>}
              style={{ borderRadius: 20, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
              extra={<Button type="link" onClick={() => navigate('/runs')}>查看全部</Button>}
            >
              <Table
                dataSource={recentExecutions}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={false}
                size="middle"
              />
            </Card>
          </motion.div>
        </Col>
      </Row>
    </div>
  );
};

export default ReportDashboardPage;
