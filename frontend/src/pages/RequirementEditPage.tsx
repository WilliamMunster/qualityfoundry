/**
 * 需求编辑/新建页面
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Form, Input, Button, Space, Select, Spin, message, Modal } from "antd";
import { ArrowLeftOutlined, SaveOutlined } from "@ant-design/icons";
import {
  getRequirement,
  createRequirement,
  updateRequirement,
  type Requirement,
  type RequirementCreate,
} from "../api/requirements";

const { TextArea } = Input;

const RequirementEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [modal, contextHolder] = Modal.useModal();
  const isEdit = !!id;

  useEffect(() => {
    if (id) {
      loadRequirement(id);
    }
  }, [id]);

  const loadRequirement = async (reqId: string) => {
    setLoading(true);
    try {
      const data = await getRequirement(reqId);
      form.setFieldsValue({
        title: data.title,
        content: data.content,
        version: data.version,
        status: data.status,
      });
    } catch (error) {
      message.error("加载需求详情失败");
      navigate("/requirements");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (
    values: RequirementCreate & { status?: string }
  ) => {
    modal.confirm({
      title: isEdit ? "确认保存" : "确认创建",
      content: isEdit ? "确定要保存对需求的修改吗？" : "确定要创建这个新需求吗？",
      onOk: async () => {
        setSaving(true);
        try {
          if (isEdit) {
            await updateRequirement(id!, values);
            message.success("更新成功");
            navigate(`/requirements/${id}`);
          } else {
            const newReq = await createRequirement(values);
            message.success("创建成功");
            navigate(`/requirements/${newReq.id}`);
          }
        } catch (error) {
          message.error(isEdit ? "更新失败" : "创建失败");
        } finally {
          setSaving(false);
        }
      }
    });
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 400,
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {contextHolder}
      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/requirements")}
        >
          返回列表
        </Button>
      </div>

      <Card title={isEdit ? "编辑需求" : "新建需求"}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ version: "v1.0", status: "draft" }}
          style={{ maxWidth: 800 }}
        >
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: "请输入标题" }]}
          >
            <Input placeholder="请输入需求标题" />
          </Form.Item>

          <Form.Item
            name="version"
            label="版本"
            rules={[{ required: true, message: "请输入版本号" }]}
          >
            <Input placeholder="例如：v1.0" />
          </Form.Item>

          {isEdit && (
            <Form.Item name="status" label="状态">
              <Select>
                <Select.Option value="draft">草稿</Select.Option>
                <Select.Option value="active">激活</Select.Option>
                <Select.Option value="archived">归档</Select.Option>
              </Select>
            </Form.Item>
          )}

          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: "请输入需求内容" }]}
          >
            <TextArea rows={10} placeholder="请输入需求详细内容" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={saving}
              >
                {isEdit ? "保存修改" : "创建需求"}
              </Button>
              <Button onClick={() => navigate("/requirements")}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default RequirementEditPage;
