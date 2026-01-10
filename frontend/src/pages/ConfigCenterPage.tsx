import React, { useState, useEffect } from "react";
import {
  Card,
  Tabs,
  Form,
  Input,
  Switch,
  Button,
  message,
  Space,
  Table,
  Modal,
  InputNumber,
  Select,
  Tag,
  Tooltip,
  Divider,
  Typography,
  Alert,
} from "antd";
import {
  MailOutlined,
  ApiOutlined,
  SettingOutlined,
  RobotOutlined,
  SaveOutlined,
  ReloadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import axios from "axios";

const { TabPane } = Tabs;
const { Text, Title } = Typography;
const { TextArea } = Input;

// 接口定义
interface NotificationConfig {
  email_enabled: boolean;
  email_smtp_host: string | null;
  email_smtp_port: number;
  email_smtp_user: string | null;
  email_smtp_password: string | null;
  email_smtp_tls: boolean;
  email_from: string | null;
  email_from_name: string | null;
  webhook_enabled: boolean;
  webhook_url: string | null;
  webhook_secret: string | null;
  webhook_timeout: number;
}

interface AIConfig {
  id: string;
  name: string;
  provider: string;
  model: string;
  api_key: string;
  base_url: string | null;
  temperature: string;
  max_tokens: string;
  is_default: boolean;
  is_active: boolean;
}

interface MCPConfig {
  mcp_enabled: boolean;
  mcp_server_command: string;
  mcp_server_args: string;
  mcp_server_url: string | null;
  mcp_max_retries: number;
  mcp_timeout: number;
}

const ConfigCenterPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("notification");
  const [loading, setLoading] = useState(false);

  // 通知配置
  const [notificationForm] = Form.useForm();
  const [notificationConfig, setNotificationConfig] =
    useState<NotificationConfig | null>(null);

  // AI 配置
  const [aiConfigs, setAIConfigs] = useState<AIConfig[]>([]);
  const [aiModalVisible, setAIModalVisible] = useState(false);
  const [editingAI, setEditingAI] = useState<AIConfig | null>(null);
  const [aiForm] = Form.useForm();

  // MCP 配置
  const [mcpForm] = Form.useForm();
  const [mcpConfig, setMcpConfig] = useState<MCPConfig | null>(null);

  // 加载通知配置
  const loadNotificationConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/api/v1/configs/notification");
      setNotificationConfig(response.data);
      notificationForm.setFieldsValue(response.data);
    } catch (error) {
      console.error("加载通知配置失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 保存通知配置
  const saveNotificationConfig = async () => {
    try {
      const values = await notificationForm.validateFields();
      setLoading(true);
      await axios.put("/api/v1/configs/notification", values);
      message.success("通知配置保存成功");
      loadNotificationConfig();
    } catch (error) {
      message.error("保存失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 加载 AI 配置
  const loadAIConfigs = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/api/v1/ai-configs");
      setAIConfigs(response.data);
    } catch (error) {
      console.error("加载 AI 配置失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 保存 AI 配置
  const saveAIConfig = async () => {
    try {
      const values = await aiForm.validateFields();
      setLoading(true);

      if (editingAI) {
        await axios.put(`/api/v1/ai-configs/${editingAI.id}`, values);
        message.success("AI 配置更新成功");
      } else {
        await axios.post("/api/v1/ai-configs", values);
        message.success("AI 配置创建成功");
      }

      setAIModalVisible(false);
      loadAIConfigs();
    } catch (error) {
      message.error("保存失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 删除 AI 配置
  const deleteAIConfig = async (id: string) => {
    Modal.confirm({
      title: "确认删除",
      content: "确定要删除这个 AI 配置吗？",
      onOk: async () => {
        try {
          await axios.delete(`/api/v1/ai-configs/${id}`);
          message.success("删除成功");
          loadAIConfigs();
        } catch (error) {
          message.error("删除失败");
        }
      },
    });
  };

  // 加载 MCP 配置
  const loadMCPConfig = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/api/v1/configs/mcp");
      setMcpConfig(response.data);
      mcpForm.setFieldsValue(response.data);
    } catch (error) {
      console.error("加载 MCP 配置失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 保存 MCP 配置
  const saveMCPConfig = async () => {
    try {
      const values = await mcpForm.validateFields();
      setLoading(true);
      await axios.put("/api/v1/configs/mcp", values);
      message.success("MCP 配置保存成功");
      loadMCPConfig();
    } catch (error) {
      message.error("保存失败");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotificationConfig();
    loadAIConfigs();
    loadMCPConfig();
  }, []);

  // AI 配置表格列
  const aiColumns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "提供商",
      dataIndex: "provider",
      key: "provider",
      render: (text: string) => (
        <Tag
          color={
            text === "openai"
              ? "green"
              : text === "deepseek"
              ? "blue"
              : "default"
          }
        >
          {text.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: "模型",
      dataIndex: "model",
      key: "model",
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean, record: AIConfig) => (
        <Space>
          {active ? (
            <Tag color="success" icon={<CheckCircleOutlined />}>
              启用
            </Tag>
          ) : (
            <Tag color="default" icon={<CloseCircleOutlined />}>
              禁用
            </Tag>
          )}
          {record.is_default && <Tag color="gold">默认</Tag>}
        </Space>
      ),
    },
    {
      title: "操作",
      key: "action",
      render: (_: any, record: AIConfig) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingAI(record);
              aiForm.setFieldsValue(record);
              setAIModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => deleteAIConfig(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: "24px" }}>
      <Title level={2}>
        <SettingOutlined /> 配置中心
      </Title>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 通知配置 */}
          <TabPane
            tab={
              <span>
                <MailOutlined />
                通知配置
              </span>
            }
            key="notification"
          >
            <Alert
              message="通知配置"
              description="配置邮件通知和 Webhook 通知，用于审核流程的自动通知。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form
              form={notificationForm}
              layout="vertical"
              initialValues={notificationConfig || {}}
            >
              {/* 邮件配置 */}
              <Divider orientation="left">
                <MailOutlined /> 邮件配置
              </Divider>

              <Form.Item
                name="email_enabled"
                label="启用邮件通知"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                }}
              >
                <Form.Item
                  name="email_smtp_host"
                  label="SMTP 服务器"
                  rules={[
                    {
                      required: notificationForm.getFieldValue("email_enabled"),
                    },
                  ]}
                >
                  <Input placeholder="smtp.example.com" />
                </Form.Item>

                <Form.Item name="email_smtp_port" label="SMTP 端口">
                  <InputNumber min={1} max={65535} style={{ width: "100%" }} />
                </Form.Item>

                <Form.Item name="email_smtp_user" label="SMTP 用户名">
                  <Input placeholder="user@example.com" />
                </Form.Item>

                <Form.Item name="email_smtp_password" label="SMTP 密码">
                  <Input.Password placeholder="留空表示不修改" />
                </Form.Item>

                <Form.Item name="email_from" label="发件人邮箱">
                  <Input placeholder="noreply@example.com" />
                </Form.Item>

                <Form.Item name="email_from_name" label="发件人名称">
                  <Input placeholder="QualityFoundry" />
                </Form.Item>
              </div>

              <Form.Item
                name="email_smtp_tls"
                label="启用 TLS"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              {/* Webhook 配置 */}
              <Divider orientation="left">
                <ApiOutlined /> Webhook 配置
              </Divider>

              <Form.Item
                name="webhook_enabled"
                label="启用 Webhook 通知"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "2fr 1fr",
                  gap: "16px",
                }}
              >
                <Form.Item name="webhook_url" label="Webhook URL">
                  <Input placeholder="https://your-service.com/webhook" />
                </Form.Item>

                <Form.Item name="webhook_timeout" label="超时时间（秒）">
                  <InputNumber min={1} max={60} style={{ width: "100%" }} />
                </Form.Item>
              </div>

              <Form.Item name="webhook_secret" label="Webhook 密钥">
                <Input.Password placeholder="留空表示不修改" />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={saveNotificationConfig}
                    loading={loading}
                  >
                    保存配置
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={loadNotificationConfig}
                  >
                    重新加载
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </TabPane>

          {/* AI 配置 */}
          <TabPane
            tab={
              <span>
                <RobotOutlined />
                AI 配置
              </span>
            }
            key="ai"
          >
            <Alert
              message="AI 模型配置"
              description="配置 AI 模型用于场景生成和用例生成。支持 OpenAI、DeepSeek 等兼容接口。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  setEditingAI(null);
                  aiForm.resetFields();
                  setAIModalVisible(true);
                }}
              >
                新建 AI 配置
              </Button>
            </div>

            <Table
              dataSource={aiConfigs}
              columns={aiColumns}
              rowKey="id"
              loading={loading}
            />
          </TabPane>

          {/* MCP 配置 */}
          <TabPane
            tab={
              <span>
                <ApiOutlined />
                MCP 配置
              </span>
            }
            key="mcp"
          >
            <Alert
              message="MCP 执行配置"
              description="配置 MCP (Model Context Protocol) 服务器用于测试执行。支持 Playwright MCP 等自动化执行工具。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form
              form={mcpForm}
              layout="vertical"
              initialValues={mcpConfig || {}}
            >
              <Form.Item
                name="mcp_enabled"
                label="启用 MCP 执行模式"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Divider orientation="left">
                <ApiOutlined /> 服务器配置
              </Divider>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 2fr",
                  gap: "16px",
                }}
              >
                <Form.Item name="mcp_server_command" label="服务器命令">
                  <Input placeholder="npx" />
                </Form.Item>

                <Form.Item name="mcp_server_args" label="服务器参数">
                  <Input placeholder="-y @modelcontextprotocol/server-playwright" />
                </Form.Item>
              </div>

              <Form.Item
                name="mcp_server_url"
                label="MCP 服务器 URL（可选，用于远程服务器）"
              >
                <Input placeholder="例如：http://localhost:3000" />
              </Form.Item>

              <Divider orientation="left">
                <SettingOutlined /> 执行参数
              </Divider>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                }}
              >
                <Form.Item name="mcp_max_retries" label="最大重试次数">
                  <InputNumber min={0} max={10} style={{ width: "100%" }} />
                </Form.Item>

                <Form.Item name="mcp_timeout" label="超时时间（秒）">
                  <InputNumber min={5} max={300} style={{ width: "100%" }} />
                </Form.Item>
              </div>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    icon={<SaveOutlined />}
                    onClick={saveMCPConfig}
                    loading={loading}
                  >
                    保存配置
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadMCPConfig}>
                    重新加载
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </TabPane>

          {/* 系统配置 */}
          <TabPane
            tab={
              <span>
                <SettingOutlined />
                系统配置
              </span>
            }
            key="system"
          >
            <Alert
              message="系统配置"
              description="配置系统级别的参数，如系统名称、维护模式等。"
              type="info"
              showIcon
              style={{ marginBottom: 24 }}
            />

            <Form layout="vertical">
              <Form.Item
                label="系统名称"
                name="system_name"
                initialValue="QualityFoundry"
              >
                <Input />
              </Form.Item>

              <Form.Item
                label="维护模式"
                name="maintenance_mode"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>

              <Form.Item>
                <Button type="primary" icon={<SaveOutlined />}>
                  保存配置
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>
      </Card>

      {/* AI 配置编辑弹窗 */}
      <Modal
        title={editingAI ? "编辑 AI 配置" : "新建 AI 配置"}
        open={aiModalVisible}
        onOk={saveAIConfig}
        onCancel={() => setAIModalVisible(false)}
        confirmLoading={loading}
        width={600}
      >
        <Form form={aiForm} layout="vertical">
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: "请输入配置名称" }]}
          >
            <Input placeholder="例如：DeepSeek 生成" />
          </Form.Item>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <Form.Item
              name="provider"
              label="提供商"
              rules={[{ required: true, message: "请选择提供商" }]}
            >
              <Select>
                <Select.Option value="openai">OpenAI</Select.Option>
                <Select.Option value="deepseek">DeepSeek</Select.Option>
                <Select.Option value="anthropic">Anthropic</Select.Option>
                <Select.Option value="other">其他</Select.Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="model"
              label="模型"
              rules={[{ required: true, message: "请输入模型名称" }]}
            >
              <Input placeholder="例如：gpt-4、deepseek-chat" />
            </Form.Item>
          </div>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: !editingAI, message: "请输入 API Key" }]}
          >
            <Input.Password
              placeholder={editingAI ? "留空表示不修改" : "请输入 API Key"}
            />
          </Form.Item>

          <Form.Item name="base_url" label="API Base URL">
            <Input placeholder="例如：https://api.deepseek.com/v1" />
          </Form.Item>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <Form.Item
              name="temperature"
              label="Temperature"
              initialValue="0.7"
            >
              <Input placeholder="0.0 - 1.0" />
            </Form.Item>

            <Form.Item name="max_tokens" label="Max Tokens" initialValue="4096">
              <Input placeholder="例如：4096" />
            </Form.Item>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <Form.Item
              name="is_default"
              label="设为默认"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>

            <Form.Item
              name="is_active"
              label="启用"
              valuePropName="checked"
              initialValue={true}
            >
              <Switch />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigCenterPage;
