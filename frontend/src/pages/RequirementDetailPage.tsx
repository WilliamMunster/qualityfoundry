/**
 * 需求详情页面
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Button,
  Space,
  Tag,
  Spin,
  message,
  Modal,
} from "antd";
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import {
  getRequirement,
  deleteRequirement,
  type Requirement,
} from "../api/requirements";

const RequirementDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [loading, setLoading] = useState(true);
  const [modal, contextHolder] = Modal.useModal();

  useEffect(() => {
    if (id) {
      loadRequirement(id);
    }
  }, [id]);

  const loadRequirement = async (reqId: string) => {
    setLoading(true);
    try {
      const data = await getRequirement(reqId);
      setRequirement(data);
    } catch (error) {
      message.error("加载需求详情失败");
      navigate("/requirements");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = () => {
    modal.confirm({
      title: "确认删除",
      content: "确定要删除这个需求吗？此操作不可恢复。",
      okType: "danger",
      onOk: async () => {
        try {
          await deleteRequirement(id!);
          message.success("删除成功");
          navigate("/requirements");
        } catch (error) {
          message.error("删除失败");
        }
      },
    });
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      draft: "default",
      active: "green",
      archived: "gray",
    };
    return colorMap[status] || "default";
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

  if (!requirement) {
    return <div>需求不存在</div>;
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

      <Card
        title={
          <Space>
            <span>需求详情</span>
            <Tag color={getStatusColor(requirement.status)}>
              {requirement.status}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => navigate(`/requirements/${id}/edit`)}
            >
              编辑
            </Button>
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              删除
            </Button>
          </Space>
        }
      >
        <Descriptions bordered column={2}>
          <Descriptions.Item label="ID" span={2}>
            {requirement.id}
          </Descriptions.Item>
          <Descriptions.Item label="标题" span={2}>
            {requirement.title}
          </Descriptions.Item>
          <Descriptions.Item label="版本">
            {requirement.version}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(requirement.status)}>
              {requirement.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(requirement.created_at).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {new Date(requirement.updated_at).toLocaleString()}
          </Descriptions.Item>
          {requirement.file_path && (
            <Descriptions.Item label="文件路径" span={2}>
              {requirement.file_path}
            </Descriptions.Item>
          )}
          <Descriptions.Item label="内容" span={2}>
            <div
              style={{
                whiteSpace: "pre-wrap",
                maxHeight: 400,
                overflow: "auto",
              }}
            >
              {requirement.content}
            </div>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default RequirementDetailPage;
