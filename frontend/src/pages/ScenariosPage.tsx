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
import { useAppStore } from "../store";

interface Scenario {
  id: string;
  requirement_id: string;
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
  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

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

  // 审核场景
  const handleApprove = (id: string) => {
    modal.confirm({
      title: "确认审核",
      content: "确定要批准这个场景吗？",
      onOk: async () => {
        try {
          await apiClient.post(`/api/v1/scenarios/${id}/approve`);
          message.success("审核通过");
          // loadScenarios();
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

  // AI 生成场景
  // AI 生成场景
  const handleGenerate = async () => {
    if (!selectedRequirement) {
      message.warning("请选择需求");
      return;
    }
    setGenerating(true);
    // 显示全局 loading
    setGlobalLoading(true, "AI 正在深度思考并生成场景中 (预计 30-60 秒)...");

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.post("/api/v1/scenarios/generate", {
        requirement_id: selectedRequirement,
      });

      const count = data?.length || 0;
      message.success(`成功生成 ${count} 个场景`);
      setGenerateModalVisible(false);
      setSelectedRequirement(""); // 清空选择
      setPage(1); // 重置到第一页
      loadScenarios();
    } catch (error) {
      console.error(error);
      // global error handler
    } finally {
      setGlobalLoading(false); // 关闭 global loading
      setGenerating(false);
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
      dataIndex: "id",
      key: "id",
      width: 100,
      ellipsis: true,
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
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            loadRequirements();
            setGenerateModalVisible(true);
          }}
        >
          AI 生成场景
        </Button>
      </div>

      <Table
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
        </Form>
      </Modal>
    </div>
  );
};

export default ScenariosPage;
