/**
 * 用例列表页面
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Table, Button, Space, Tag, message, Modal, Select, Form } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import axios from "axios";

interface TestCase {
  id: string;
  scenario_id: string;
  title: string;
  steps: string[];
  approval_status: string;
  created_at: string;
}

interface Scenario {
  id: string;
  title: string;
}

const TestCasesPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [testcases, setTestcases] = useState<TestCase[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<string>("");

  // 加载用例列表
  const loadTestcases = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/api/v1/testcases");
      setTestcases(response.data.items || []);
    } catch (error) {
      message.error("加载用例列表失败");
    } finally {
      setLoading(false);
    }
  };

  // 加载场景列表
  const loadScenarios = async () => {
    try {
      const response = await axios.get("/api/v1/scenarios");
      setScenarios(response.data.items || []);
    } catch (error) {
      console.error("加载场景列表失败");
    }
  };

  useEffect(() => {
    loadTestcases();
    loadScenarios();

    // 如果 URL 中有 scenario_id，自动打开生成弹窗
    const scenarioId = searchParams.get("scenario_id");
    if (scenarioId) {
      setSelectedScenario(scenarioId);
      setGenerateModalVisible(true);
    }
  }, []);

  // 审核用例
  const handleApprove = (id: string) => {
    Modal.confirm({
      title: "确认审核",
      content: "确定要批准这个用例吗？",
      onOk: async () => {
        try {
          await axios.post(`/api/v1/testcases/${id}/approve`);
          message.success("审核通过");
          loadTestcases();
        } catch (error) {
          message.error("审核失败");
        }
      },
    });
  };

  // AI 生成用例
  const handleGenerate = async () => {
    if (!selectedScenario) {
      message.warning("请选择场景");
      return;
    }
    setGenerating(true);
    try {
      await axios.post("/api/v1/testcases/generate", {
        scenario_id: selectedScenario,
      });
      message.success("用例生成成功");
      setGenerateModalVisible(false);
      loadTestcases();
    } catch (error) {
      message.error("用例生成失败");
    } finally {
      setGenerating(false);
    }
  };

  // 执行用例
  const handleExecute = async (id: string) => {
    try {
      await axios.post("/api/v1/executions", {
        testcase_id: id,
        mode: "dsl",
      });
      message.success("执行任务已创建");
      navigate("/executions");
    } catch (error) {
      message.error("创建执行任务失败");
    }
  };

  // 删除用例
  const handleDelete = (id: string) => {
    Modal.confirm({
      title: "确认删除",
      content: "确定要删除这个用例吗？",
      onOk: async () => {
        try {
          await axios.delete(`/api/v1/testcases/${id}`);
          message.success("删除成功");
          loadTestcases();
        } catch (error) {
          message.error("删除失败");
        }
      },
    });
  };

  const columns: ColumnsType<TestCase> = [
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
      width: 300,
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
            onClick={() => handleExecute(record.id)}
          >
            执行
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
        <h2>用例管理</h2>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setGenerateModalVisible(true)}
        >
          AI 生成用例
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={testcases}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title="AI 生成用例"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalVisible(false)}
        confirmLoading={generating}
      >
        <Form layout="vertical">
          <Form.Item label="选择场景" required>
            <Select
              placeholder="请选择场景"
              value={selectedScenario}
              onChange={setSelectedScenario}
              style={{ width: "100%" }}
            >
              {scenarios.map((s) => (
                <Select.Option key={s.id} value={s.id}>
                  {s.title}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TestCasesPage;
