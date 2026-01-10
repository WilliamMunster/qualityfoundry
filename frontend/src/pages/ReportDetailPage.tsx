/**
 * 报告详情页面
 *
 * 展示单个执行的详细信息：状态、步骤、日志、结果
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Tag,
  Timeline,
  Button,
  Spin,
  Alert,
  Progress,
  Divider,
  Space,
  Typography,
} from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ArrowLeftOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import axios from "axios";

const { Text, Title } = Typography;

interface ExecutionDetail {
  id: string;
  testcase_id: string;
  environment_id: string | null;
  mode: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface ExecutionStatus {
  id: string;
  status: string;
  progress: number | null;
  current_step: string | null;
  message: string | null;
}

interface ExecutionLogs {
  execution_id: string;
  logs: string[];
}

const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [execution, setExecution] = useState<ExecutionDetail | null>(null);
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 加载执行详情
  const loadExecution = async () => {
    if (!id) return;

    try {
      const [execRes, statusRes, logsRes] = await Promise.all([
        axios.get(`/api/v1/executions/${id}`),
        axios.get(`/api/v1/executions/${id}/status`),
        axios.get(`/api/v1/executions/${id}/logs`),
      ]);

      setExecution(execRes.data);
      setStatus(statusRes.data);
      setLogs(logsRes.data.logs || []);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecution();

    // 如果正在运行，定时刷新
    const interval = setInterval(() => {
      if (status?.status === "running" || status?.status === "pending") {
        loadExecution();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [id, status?.status]);

  // 状态标签
  const getStatusTag = (statusStr: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: "default", icon: <ClockCircleOutlined /> },
      running: { color: "processing", icon: <SyncOutlined spin /> },
      success: { color: "success", icon: <CheckCircleOutlined /> },
      failed: { color: "error", icon: <CloseCircleOutlined /> },
      stopped: { color: "warning", icon: <ClockCircleOutlined /> },
    };
    const cfg = config[statusStr] || config.pending;
    return (
      <Tag color={cfg.color} icon={cfg.icon}>
        {statusStr.toUpperCase()}
      </Tag>
    );
  };

  // 计算执行时长
  const getDuration = () => {
    if (!execution?.started_at) return "-";
    const start = new Date(execution.started_at);
    const end = execution.completed_at
      ? new Date(execution.completed_at)
      : new Date();
    const diffMs = end.getTime() - start.getTime();
    const seconds = Math.floor(diffMs / 1000);
    if (seconds < 60) return `${seconds} 秒`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes} 分 ${remainingSeconds} 秒`;
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
        <p>加载中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={<Button onClick={() => navigate(-1)}>返回</Button>}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 头部 */}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            执行报告详情
          </Title>
        </Space>
        <Button icon={<ReloadOutlined />} onClick={loadExecution}>
          刷新
        </Button>
      </div>

      {/* 基本信息 */}
      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="执行 ID">
            <Text copyable>{execution?.id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="执行状态">
            {getStatusTag(execution?.status || "pending")}
          </Descriptions.Item>
          <Descriptions.Item label="执行模式">
            <Tag>{execution?.mode?.toUpperCase()}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="执行时长">
            {getDuration()}
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {execution?.started_at
              ? new Date(execution.started_at).toLocaleString()
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {execution?.completed_at
              ? new Date(execution.completed_at).toLocaleString()
              : "-"}
          </Descriptions.Item>
          <Descriptions.Item label="测试用例 ID" span={2}>
            <Text copyable>{execution?.testcase_id}</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 执行进度 */}
      {(status?.status === "running" || status?.status === "pending") && (
        <Card title="执行进度" style={{ marginBottom: 16 }}>
          <Progress
            percent={status?.progress || 0}
            status={status?.status === "running" ? "active" : "normal"}
          />
          {status?.current_step && (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">当前步骤: </Text>
              <Text strong>{status.current_step}</Text>
            </div>
          )}
          {status?.message && (
            <div style={{ marginTop: 4 }}>
              <Text type="secondary">{status.message}</Text>
            </div>
          )}
        </Card>
      )}

      {/* 执行日志 */}
      <Card title="执行日志" style={{ marginBottom: 16 }}>
        {logs.length > 0 ? (
          <Timeline>
            {logs.map((log, index) => (
              <Timeline.Item
                key={index}
                color={
                  log.includes("失败") || log.includes("错误")
                    ? "red"
                    : log.includes("成功")
                    ? "green"
                    : "blue"
                }
              >
                <Text style={{ fontFamily: "monospace", fontSize: 12 }}>
                  {log}
                </Text>
              </Timeline.Item>
            ))}
          </Timeline>
        ) : (
          <Text type="secondary">暂无日志</Text>
        )}
      </Card>

      {/* 操作按钮 */}
      <Card>
        <Space>
          <Button type="primary" onClick={() => navigate(`/testcases`)}>
            查看用例列表
          </Button>
          <Button onClick={() => navigate(`/executions`)}>返回执行列表</Button>
        </Space>
      </Card>
    </div>
  );
};

export default ReportDetailPage;
