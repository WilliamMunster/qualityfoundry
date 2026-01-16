/**
 * 场景列表页面
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Table,
  Button,
  Space,
  Tag,
  message,
  Modal,
  Select,
  Form,
  Input,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import apiClient from "../api/client";
import { getRequirements, type Requirement } from "../api/requirements";
import { batchDeleteScenarios } from "../api/scenarios";
import { useAppStore } from "../store";

interface Scenario {
  id: string;
  seq_id?: number;
  requirement_id: string;
  requirement_seq_id?: number;
  title: string;
  description?: string;
  steps: string[];
  approval_status: string;
  created_at: string;
}

const ScenariosPage: React.FC = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<string>("");
  const [selectedConfig, setSelectedConfig] = useState<string | undefined>(undefined);
  const [aiConfigs, setAiConfigs] = useState<any[]>([]);
  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const { setLoading: setGlobalLoading } = useAppStore();

  const [modal, contextHolder] = Modal.useModal();

  // 加载场景列表
  const loadScenarios = async () => {
    setLoading(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get("/api/v1/scenarios", {
        params: {
          page,
          page_size: pageSize,
        },
      });
      setScenarios(data.items || []);
      setTotal(data.total || 0);
      setSelectedRowKeys([]);
    } catch (error) {
      // global error handler
    } finally {
      setLoading(false);
    }
  };

  // 加载需求列表
  const loadRequirements = async () => {
    try {
      const data = await getRequirements({
        page: 1,
        page_size: 100,
      });
      setRequirements(data.items || []);
    } catch (error) {
      console.error("加载需求列表失败");
    }
  };

  useEffect(() => {
    loadScenarios();
  }, [page, pageSize]);

  useEffect(() => {
    loadRequirements();
  }, []);

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return;

    modal.confirm({
      title: "确认批量删除",
      content: `确定要删除选中的 ${selectedRowKeys.length} 个场景吗？`,
      onOk: async () => {
        try {
          await batchDeleteScenarios(selectedRowKeys as string[]);
          message.success("批量删除成功");
          loadScenarios();
        } catch (error) {
          // 全局错误处理器已显示详细错误消息
        }
      },
    });
  };

  // 审核场景
  const handleApprove = (id: string) => {
    modal.confirm({
      title: "确认审核",
      content: "确定要批准这个场景吗？",
      onOk: async () => {
        try {
          await apiClient.post(`/api/v1/scenarios/${id}/approve?reviewer=admin`);
          message.success("审核通过");
          setScenarios((prev) =>
            prev.map((item) =>
              item.id === id ? { ...item, approval_status: "approved" } : item
            )
          );
        } catch (error) {
          // global error handler
        }
      },
    });
  };

  // 批量审核（通过）
  const handleBatchApprove = () => {
    const pendingIds = selectedRowKeys.filter((key) => {
      const scenario = scenarios.find((s) => s.id === key);
      return scenario?.approval_status === "pending";
    });

    if (pendingIds.length === 0) {
      message.warning("请选择待审核状态的场景");
      return;
    }

    modal.confirm({
      title: "批量审核通过",
      content: `确定要批准选中的 ${pendingIds.length} 个场景吗？`,
      onOk: async () => {
        try {
          await apiClient.post("/api/v1/scenarios/batch-approve", {
            entity_type: "scenario",
            entity_ids: pendingIds,
            reviewer: "admin",
          });
          message.success(`成功审核通过 ${pendingIds.length} 个场景`);
          setScenarios((prev) =>
            prev.map((item) =>
              pendingIds.includes(item.id)
                ? { ...item, approval_status: "approved" }
                : item
            )
          );
          setSelectedRowKeys([]);
        } catch (error) {
          // global error handler
        }
      },
    });
  };

  // 批量审核（拒绝）
  const handleBatchReject = () => {
    const pendingIds = selectedRowKeys.filter((key) => {
      const scenario = scenarios.find((s) => s.id === key);
      return scenario?.approval_status === "pending";
    });

    if (pendingIds.length === 0) {
      message.warning("请选择待审核状态的场景");
      return;
    }

    modal.confirm({
      title: "批量审核拒绝",
      content: `确定要拒绝选中的 ${pendingIds.length} 个场景吗？`,
      onOk: async () => {
        try {
          await apiClient.post("/api/v1/scenarios/batch-reject", {
            entity_type: "scenario",
            entity_ids: pendingIds,
            reviewer: "admin",
          });
          message.success(`成功拒绝 ${pendingIds.length} 个场景`);
          setScenarios((prev) =>
            prev.map((item) =>
              pendingIds.includes(item.id)
                ? { ...item, approval_status: "rejected" }
                : item
            )
          );
          setSelectedRowKeys([]);
        } catch (error) {
          // global error handler
        }
      },
    });
  };

  // 加载 AI 配置
  const loadAiConfigs = async () => {
    try {
      const data: any = await apiClient.get("/api/v1/ai-configs", { params: { is_active: true } });
      setAiConfigs(data || []);
    } catch (error) {
      console.error("加载 AI 配置失败");
    }
  };

  // AI 生成场景
  const handleGenerate = async () => {
    if (!selectedRequirement) {
      message.warning("请选择需求");
      return;
    }
    setGenerating(true);
    // 显示全局 loading
    setGlobalLoading(true, "AI 正在深度思考并生成场景中 (预计 30-120 秒)...");
    setGenerateModalVisible(false);

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.post("/api/v1/scenarios/generate", {
        requirement_id: selectedRequirement,
        config_id: selectedConfig,
      });

      const count = data?.length || 0;
      message.success(`成功生成 ${count} 个场景`);
      setSelectedRequirement(""); // 清空选择
      setPage(1); // 重置到第一页
      loadScenarios();
    } catch (error) {
      console.error(error);
      // global error handler
    } finally {
      setGlobalLoading(false); // 关闭 global loading
      setGenerating(false);
      setSelectedConfig(undefined);
    }
  };

  // 删除场景
  const handleDelete = (id: string) => {
    modal.confirm({
      title: "确认删除",
      content: "确定要删除这个场景吗？",
      onOk: async () => {
        try {
          await apiClient.delete(`/api/v1/scenarios/${id}`);
          message.success("删除成功");
          // loadScenarios();
          setScenarios((prev) => prev.filter((item) => item.id !== id));
          setTotal((prev) => prev - 1);
        } catch (error) {
          // global error handler
        }
      },
    });
  };

  const columns: ColumnsType<Scenario> = [
    {
      title: "ID",
      dataIndex: "seq_id",
      key: "seq_id",
      width: 80,
      render: (seq_id: number) => seq_id || "-",
    },
    {
      title: "需求ID",
      dataIndex: "requirement_seq_id",
      key: "requirement_seq_id",
      width: 80,
      render: (seq_id: number) => seq_id || "-",
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
    },
    {
      title: "步骤数",
      dataIndex: "steps",
      key: "steps",
      width: 100,
      render: (steps: string[]) => steps?.length || 0,
    },
    {
      title: "审核状态",
      dataIndex: "approval_status",
      key: "approval_status",
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: "orange",
          approved: "green",
          rejected: "red",
        };
        return <Tag color={colorMap[status] || "default"}>{status}</Tag>;
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
      width: 280,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() =>
              modal.info({
                title: record.title,
                width: 600,
                content: (
                  <div>
                    <p>
                      <strong>描述：</strong>
                      {record.description || "无"}
                    </p>
                    <p>
                      <strong>步骤：</strong>
                    </p>
                    <ul style={{ paddingLeft: 20 }}>
                      {record.steps?.map((step, i) => (
                        <li key={i} style={{ listStyleType: 'none' }}>{step}</li>
                      ))}
                    </ul>
                  </div>
                ),
              })
            }
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/testcases?scenario_id=${record.id}`)}
          >
            生成用例
          </Button>
          {record.approval_status === "pending" && (
            <Button
              type="link"
              size="small"
              onClick={() => handleApprove(record.id)}
            >
              审核
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
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
        <h2>场景管理</h2>
        <Space>
          {selectedRowKeys.length > 0 && (
            <>
              <Button type="primary" onClick={handleBatchApprove}>
                批量通过 ({selectedRowKeys.length})
              </Button>
              <Button onClick={handleBatchReject}>
                批量拒绝 ({selectedRowKeys.length})
              </Button>
              <Button danger onClick={handleBatchDelete}>
                批量删除 ({selectedRowKeys.length})
              </Button>
            </>
          )}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              loadRequirements();
              loadAiConfigs();
              setGenerateModalVisible(true);
            }}
          >
            AI 生成场景
          </Button>
        </Space>
      </div>

      <Table
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        columns={columns}
        dataSource={scenarios}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, pageSize) => {
            setPage(page);
            setPageSize(pageSize);
          },
        }}
      />

      <Modal
        title="AI 生成场景"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalVisible(false)}
        confirmLoading={generating}
        okButtonProps={{ disabled: !selectedRequirement }}
        okText="开始生成"
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="选择需求" required>
            <Select
              placeholder="请选择需求"
              value={selectedRequirement}
              onChange={setSelectedRequirement}
              style={{ width: "100%" }}
            >
              {requirements.map((req) => (
                <Select.Option key={req.id} value={req.id}>
                  {req.title}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="AI 配置 (可选)">
            <Select
              placeholder="使用默认配置"
              value={selectedConfig}
              onChange={setSelectedConfig}
              allowClear
              style={{ width: "100%" }}
            >
              {aiConfigs.map((config) => (
                <Select.Option key={config.id} value={config.id}>
                  {config.name} ({config.model})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScenariosPage;
