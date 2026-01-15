/**
 * 报告仪表板页面
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Row, Col, Statistic, Table, Tag, Button } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import apiClient from "../api/client";

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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const [statsData, execData]: [any, any] = await Promise.all([
          apiClient.get("/api/v1/reports/dashboard-stats"),
          apiClient.get("/api/v1/executions", {
            params: { page: 1, page_size: 10 },
          }),
        ]);
        setStats(statsData);
        setRecentExecutions(execData.items || []);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getStatusTag = (status: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: "default", icon: <ClockCircleOutlined /> },
      running: { color: "processing", icon: <SyncOutlined spin /> },
      success: { color: "success", icon: <CheckCircleOutlined /> },
      failed: { color: "error", icon: <CloseCircleOutlined /> },
      stopped: { color: "warning", icon: <ClockCircleOutlined /> },
    };
    const cfg = config[status] || config.pending;
    return (
      <Tag color={cfg.color} icon={cfg.icon}>
        {status.toUpperCase()}
      </Tag>
    );
  };

  const columns = [
    {
      title: "执行ID",
      dataIndex: "id",
      key: "id",
      width: 100,
      ellipsis: true,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: "模式",
      dataIndex: "mode",
      key: "mode",
      width: 80,
      render: (mode: string) => <Tag>{mode?.toUpperCase()}</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_: any, record: Execution) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/reports/${record.id}`)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>测试报告仪表板</h2>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总执行次数"
              value={stats.total}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功"
              value={stats.success}
              valueStyle={{ color: "#3f8600" }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failed}
              valueStyle={{ color: "#cf1322" }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.running}
              valueStyle={{ color: "#1890ff" }}
              prefix={<SyncOutlined spin={stats.running > 0} />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="最近执行记录"
        style={{ marginTop: 24 }}
        extra={
          <Button onClick={() => navigate("/executions")}>查看全部</Button>
        }
      >
        <Table
          dataSource={recentExecutions}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
};

export default ReportDashboardPage;
