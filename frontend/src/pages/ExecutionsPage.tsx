/**
 * 执行管理页面
 */
import React, { useEffect, useState } from "react";
import { Table, Button, Space, Tag, Select, Modal } from "antd";
import { message } from "../components/AntdGlobal";
import { PlayCircleOutlined, StopOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import apiClient from "../api/client";

interface Execution {
  id: string;
  testcase_id: string;
  environment_id: string;
  mode: string;
  status: string;
  result?: object;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

interface Environment {
  id: string;
  name: string;
}

const ExecutionsPage: React.FC = () => {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [selectedEnv, setSelectedEnv] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [modal, contextHolder] = Modal.useModal();

  // 加载执行记录
  const loadExecutions = async () => {
    setLoading(true);
    try {
      const params = selectedEnv ? { environment_id: selectedEnv } : {};
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get("/api/v1/executions", { params });
      setExecutions(data.items || data || []);
    } catch (error) {
      // global handler
    } finally {
      setLoading(false);
    }
  };

  // 加载环境列表
  const loadEnvironments = async () => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get("/api/v1/environments");
      setEnvironments(data.items || data || []);
    } catch (error) {
      console.error("加载环境列表失败");
    }
  };

  useEffect(() => {
    loadEnvironments();
    loadExecutions();
  }, []);

  useEffect(() => {
    loadExecutions();
  }, [selectedEnv]);

  // 停止执行
  const handleStop = (id: string) => {
    modal.confirm({
      title: "确认停止",
      content: "确定要停止这个执行任务吗？",
      onOk: async () => {
        try {
          await apiClient.post(`/api/v1/executions/${id}/stop`);
          message.success("已发送停止命令");
          loadExecutions();
        } catch (error) {
          // global handler
        }
      }
    });
  };

  // 查看详情
  const handleViewDetail = (record: Execution) => {
    Modal.info({
      title: "执行详情",
      width: 600,
      content: (
        <div>
          <p>
            <strong>ID：</strong>
            {record.id}
          </p>
          <p>
            <strong>模式：</strong>
            {record.mode?.toUpperCase()}
          </p>
          <p>
            <strong>状态：</strong>
            {record.status}
          </p>
          <p>
            <strong>创建时间：</strong>
            {new Date(record.created_at).toLocaleString()}
          </p>
          {record.completed_at && (
            <p>
              <strong>完成时间：</strong>
              {new Date(record.completed_at).toLocaleString()}
            </p>
          )}
          {record.result && (
            <div>
              <strong>结果：</strong>
              <pre
                style={{ background: "#f5f5f5", padding: 8, borderRadius: 4 }}
              >
                {JSON.stringify(record.result, null, 2)}
              </pre>
            </div>
          )}
          {record.error_message && (
            <p style={{ color: "red" }}>
              <strong>错误：</strong>
              {record.error_message}
            </p>
          )}
        </div>
      ),
    });
  };

  // 查看日志
  const handleViewLogs = async (id: string) => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get(`/api/v1/executions/${id}/logs`);
      Modal.info({
        title: "执行日志",
        width: 700,
        content: (
          <pre
            style={{
              maxHeight: 400,
              overflow: "auto",
              background: "#1e1e1e",
              color: "#fff",
              padding: 12,
              borderRadius: 4,
            }}
          >
            {data.logs?.join("\n") || "暂无日志"}
          </pre>
        ),
      });
    } catch (error) {
      // global handler
    }
  };

  const columns: ColumnsType<Execution> = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 100,
      ellipsis: true,
    },
    {
      title: "执行模式",
      dataIndex: "mode",
      key: "mode",
      width: 120,
      render: (mode: string) => {
        const colorMap: Record<string, string> = {
          dsl: "blue",
          mcp: "green",
          hybrid: "purple",
        };
        return (
          <Tag color={colorMap[mode?.toLowerCase()] || "default"}>
            {mode?.toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: "执行状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: "default",
          running: "processing",
          success: "success",
          failed: "error",
          stopped: "warning",
        };
        return (
          <Tag color={colorMap[status?.toLowerCase()] || "default"}>
            {status}
          </Tag>
        );
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      width: 250,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => handleViewDetail(record)}
          >
            查看详情
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => handleViewLogs(record.id)}
          >
            查看日志
          </Button>
          {record.status?.toLowerCase() === "running" && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStop(record.id)}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <h2>执行管理</h2>
        <Space>
          <Select
            placeholder="全部环境"
            style={{ width: 150 }}
            allowClear
            value={selectedEnv}
            onChange={setSelectedEnv}
          >
            {environments.map((env) => (
              <Select.Option key={env.id} value={env.id}>
                {env.name}
              </Select.Option>
            ))}
          </Select>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={loadExecutions}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={executions}
        rowKey="id"
        loading={loading}
      />
    </div>
  );
};

export default ExecutionsPage;
