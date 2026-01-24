/**
 * 环境列表页面
 */
import React, { useEffect, useState } from "react";
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Switch,
} from "antd";
import { message } from "../components/AntdGlobal";
import {
  PlusOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getEnvironments,
  createEnvironment,
  deleteEnvironment,
  healthCheck,
  type Environment,
} from "../api/environments";

const EnvironmentsPage: React.FC = () => {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [modal, contextHolder] = Modal.useModal();

  const loadEnvironments = async () => {
    setLoading(true);
    try {
      const data = await getEnvironments();
      setEnvironments(data.items);
    } catch (error) {
      message.error("加载环境列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEnvironments();
  }, []);

  const handleCreate = (values: any) => {
    modal.confirm({
      title: "确认新建",
      content: "确定要创建这个环境吗？",
      onOk: async () => {
        try {
          await createEnvironment(values);
          message.success("创建成功");
          setModalVisible(false);
          form.resetFields();
          loadEnvironments();
        } catch (error) {
          message.error("创建失败");
        }
      }
    });
  };

  const handleDelete = (id: string) => {
    modal.confirm({
      title: "确认删除",
      content: "确定要删除这个环境吗？",
      onOk: async () => {
        try {
          await deleteEnvironment(id);
          message.success("删除成功");
          // loadEnvironments();
          setEnvironments((prev) => prev.filter((item) => item.id !== id));
        } catch (error) {
          message.error("删除失败");
        }
      },
    });
  };

  const handleHealthCheck = async (id: string) => {
    try {
      const result = await healthCheck(id);
      if (result.is_healthy) {
        message.success("健康检查通过");
      } else {
        message.warning("健康检查失败");
      }
    } catch (error) {
      message.error("健康检查失败");
    }
  };

  const columns: ColumnsType<Environment> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Base URL",
      dataIndex: "base_url",
      key: "base_url",
    },
    {
      title: "状态",
      dataIndex: "is_active",
      key: "is_active",
      render: (active: boolean) => (
        <Tag color={active ? "green" : "default"}>
          {active ? "激活" : "未激活"}
        </Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: "操作",
      key: "action",
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => handleHealthCheck(record.id)}
          >
            健康检查
          </Button>
          <Button type="link" size="small">
            编辑
          </Button>
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
        <h2>环境管理</h2>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          新建环境
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={environments}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title="新建环境"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="环境名称" rules={[{ required: true }]}>
            <Input placeholder="例如：dev, sit, uat, prod" />
          </Form.Item>
          <Form.Item
            name="base_url"
            label="Base URL"
            rules={[{ required: true }]}
          >
            <Input placeholder="http://localhost:3000" />
          </Form.Item>
          <Form.Item name="health_check_url" label="健康检查 URL">
            <Input placeholder="http://localhost:3000/health" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default EnvironmentsPage;
