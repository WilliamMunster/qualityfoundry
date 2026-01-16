/**
 * 用例列表页面
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Table, Button, Space, Tag, message, Modal, Select, Form } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import apiClient from "../api/client";
import { batchDeleteTestCases } from "../api/testcases";
import { useAppStore } from "../store";

interface TestStep {
  step: string;
  expected: string;
}

interface TestCase {
  id: string;
  seq_id?: number;
  scenario_id: string;
  scenario_seq_id?: number;
  title: string;
  steps: TestStep[];
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
  const [selectedConfig, setSelectedConfig] = useState<string | undefined>(undefined);
  const [aiConfigs, setAiConfigs] = useState<any[]>([]);
  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const { setLoading: setGlobalLoading } = useAppStore();

  const [modal, contextHolder] = Modal.useModal();

  // 加载用例列表
  const loadTestcases = async () => {
    setLoading(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get("/api/v1/testcases", {
        params: {
          page,
          page_size: pageSize,
        },
      });
      setTestcases(data.items || []);
      setTotal(data.total || 0);
      setSelectedRowKeys([]);
    } catch (error) {
      // global handler
    } finally {
      setLoading(false);
    }
  };

  // 加载场景列表
  const loadScenarios = async () => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.get("/api/v1/scenarios");
      setScenarios(data.items || []);
    } catch (error) {
      console.error("加载场景列表失败");
    }
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

  useEffect(() => {
    loadTestcases();
  }, [page, pageSize]);

  // 展开弹窗时自动刷新场景列表
  const openGenerateModal = () => {
    loadScenarios();
    loadAiConfigs();
    setGenerateModalVisible(true);
  };

  useEffect(() => {
    loadScenarios();

    // 如果 URL 中有 scenario_id，自动打开生成弹窗
    const scenarioId = searchParams.get("scenario_id");
    if (scenarioId) {
      setSelectedScenario(scenarioId);
      setGenerateModalVisible(true);
    }
  }, []);

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return;

    modal.confirm({
      title: "确认批量删除",
      content: `确定要删除选中的 ${selectedRowKeys.length} 个用例吗？`,
      onOk: async () => {
        try {
          await batchDeleteTestCases(selectedRowKeys as string[]);
          message.success("批量删除成功");
          loadTestcases();
        } catch (error) {
          // 全局错误处理器已显示详细错误消息
        }
      },
    });
  };

  // 审核用例
  const handleApprove = (id: string) => {
    modal.confirm({
      title: "确认审核",
      content: "确定要批准这个用例吗？",
      onOk: async () => {
        try {
          await apiClient.post(`/api/v1/testcases/${id}/approve?reviewer=admin`);
          message.success("审核通过");
          setTestcases((prev) =>
            prev.map((item) =>
              item.id === id ? { ...item, approval_status: "approved" } : item
            )
          );
        } catch (error) {
          // global handler
        }
      },
    });
  };

  // 批量审核（通过）
  const handleBatchApprove = () => {
    const pendingIds = selectedRowKeys.filter((key) => {
      const tc = testcases.find((t) => t.id === key);
      return tc?.approval_status === "pending";
    });

    if (pendingIds.length === 0) {
      message.warning("请选择待审核状态的用例");
      return;
    }

    modal.confirm({
      title: "批量审核通过",
      content: `确定要批准选中的 ${pendingIds.length} 个用例吗？`,
      onOk: async () => {
        try {
          await apiClient.post("/api/v1/testcases/batch-approve", {
            entity_type: "testcase",
            entity_ids: pendingIds,
            reviewer: "admin",
          });
          message.success(`成功审核通过 ${pendingIds.length} 个用例`);
          setTestcases((prev) =>
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
      const tc = testcases.find((t) => t.id === key);
      return tc?.approval_status === "pending";
    });

    if (pendingIds.length === 0) {
      message.warning("请选择待审核状态的用例");
      return;
    }

    modal.confirm({
      title: "批量审核拒绝",
      content: `确定要拒绝选中的 ${pendingIds.length} 个用例吗？`,
      onOk: async () => {
        try {
          await apiClient.post("/api/v1/testcases/batch-reject", {
            entity_type: "testcase",
            entity_ids: pendingIds,
            reviewer: "admin",
          });
          message.success(`成功拒绝 ${pendingIds.length} 个用例`);
          setTestcases((prev) =>
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

  // AI 生成用例
  const handleGenerate = async () => {
    if (!selectedScenario) {
      message.warning("请选择场景");
      return;
    }
    setGenerating(true);
    // 显示全局 loading
    setGlobalLoading(true, "AI 正在分析场景并拆解测试步骤 (预计 30-120 秒)...");
    setGenerateModalVisible(false);

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.post("/api/v1/testcases/generate", {
        scenario_id: selectedScenario,
        config_id: selectedConfig,
      });
      const count = data?.length || 0;
      message.success(`成功生成 ${count} 条测试用例`);
      setSelectedScenario(""); // 清空选择
      setPage(1); // 重置到第一页
      loadTestcases();
    } catch (error) {
      console.error(error);
      // global handler
    } finally {
      setGlobalLoading(false);
      setGenerating(false);
      setSelectedConfig(undefined);
    }
  };

  // 执行用例
  const handleExecute = (id: string) => {
    modal.confirm({
      title: "确认执行",
      content: "确定要执行这个测试用例吗？",
      onOk: async () => {
        try {
          await apiClient.post("/api/v1/executions", {
            testcase_id: id,
            mode: "dsl",
          });
          message.success("执行任务已创建");
          navigate("/executions");
        } catch (error) {
          // global handler
        }
      },
    });
  };

  // 删除用例
  const handleDelete = (id: string) => {
    modal.confirm({
      title: "确认删除",
      content: "确定要删除这个用例吗？",
      onOk: async () => {
        try {
          await apiClient.delete(`/api/v1/testcases/${id}`);
          message.success("删除成功");
          // loadTestcases();
          // loadTestcases();
          setTestcases((prev) => prev.filter((item) => item.id !== id));
          setTotal((prev) => prev - 1);
        } catch (error) {
          // global handler
        }
      },
    });
  };

  const columns: ColumnsType<TestCase> = [
    {
      title: "ID",
      dataIndex: "seq_id",
      key: "seq_id",
      width: 80,
      render: (seq_id: number) => seq_id || "-",
    },
    {
      title: "场景ID",
      dataIndex: "scenario_seq_id",
      key: "scenario_seq_id",
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
      render: (steps: TestStep[]) => steps?.length || 0,
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
              modal.info({
                title: record.title,
                width: 600,
                content: (
                  <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
                    <Table
                      dataSource={record.steps || []}
                      pagination={false}
                      size="small"
                      bordered
                      rowKey={(record, index) => index?.toString() || "0"}
                      columns={[
                        {
                          title: "步骤",
                          dataIndex: "step",
                          key: "step",
                          width: "40%",
                        },
                        {
                          title: "预期结果",
                          dataIndex: "expected",
                          key: "expected",
                          width: "60%",
                        },
                      ]}
                    />
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
      {contextHolder}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <h2>用例管理</h2>
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
            onClick={openGenerateModal}
          >
            AI 生成用例
          </Button>
        </Space>
      </div>

      <Table
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        columns={columns}
        dataSource={testcases}
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
        title="AI 生成用例"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => setGenerateModalVisible(false)}
        confirmLoading={generating}
        okButtonProps={{ disabled: !selectedScenario }}
        okText="开始生成"
        cancelText="取消"
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

export default TestCasesPage;
