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
import axios from "axios";

interface Scenario {
  id: string;
  requirement_id: string;
  title: string;
  description?: string;
  steps: string[];
  approval_status: string;
  created_at: string;
}

interface Requirement {
  id: string;
  title: string;
}

const ScenariosPage: React.FC = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedRequirement, setSelectedRequirement] = useState<string>("");

  // 加载场景列表
  const loadScenarios = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/api/v1/scenarios");
      setScenarios(response.data.items || []);
    } catch (error) {
      message.error("加载场景列表失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载需求列表
  const loadRequirements = async () => {
    try {
      const response = await axios.get("/api/v1/requirements");
      setRequirements(response.data.items || []);
    } catch (error) {
      console.error("加载需求列表失败");
    }
  };

  useEffect(() => {
    loadScenarios();
    loadRequirements();
  }, []);

  // 审核场景
  const handleApprove = (id: string) => {
    Modal.confirm({
      title: "确认审核",
      content: "确定要批准这个场景吗？",
      onOk: async () => {
        try {
          await axios.post(`/api/v1/scenarios/${id}/approve`);
          message.success("审核通过");
          loadScenarios();
        } catch (error) {
          message.error("审核失败");
        }
      },
    });
  };

  // AI 生成场景
  const handleGenerate = async () => {
    if (!selectedRequirement) {
      message.warning("请选择需求");
      return;
    }
    setGenerating(true);
    try {
      await axios.post("/api/v1/scenarios/generate", {
        requirement_id: selectedRequirement,
      });
      message.success("场景生成成功");
      setGenerateModalVisible(false);
      loadScenarios();
    } catch (error) {
      message.error("场景生成失败");
    } finally {
      setGenerating(false);
    }
  };

  // 删除场景
  const handleDelete = (id: string) => {
    Modal.confirm({
      title: "确认删除",
      content: "确定要删除这个场景吗？",
      onOk: async () => {
        try {
          await axios.delete(`/api/v1/scenarios/${id}`);
          message.success("删除成功");
          loadScenarios();
        } catch (error) {
          message.error("删除失败");
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
              Modal.info({
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
                    <ol>
                      {record.steps?.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
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
          onClick={() => setGenerateModalVisible(true)}
        >
          AI 生成场景
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={scenarios}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title="AI 生成场景"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalVisible(false)}
        confirmLoading={generating}
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
