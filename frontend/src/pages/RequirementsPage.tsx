/**
 * 需求列表页面
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Space, Input, Modal, Upload } from "antd";
import { message } from "../components/AntdGlobal";
import {
  PlusOutlined,
  UploadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getRequirements,
  deleteRequirement,
  uploadRequirement,
  batchDeleteRequirements,
  type Requirement,
} from "../api/requirements";

const { Search } = Input;

const RequirementsPage: React.FC = () => {
  const navigate = useNavigate();
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [searchText, setSearchText] = useState("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const [modal, contextHolder] = Modal.useModal();

  // 加载需求列表
  const loadRequirements = async () => {
    setLoading(true);
    try {
      const data = await getRequirements({
        page,
        page_size: pageSize,
        search: searchText || undefined,
      });
      setRequirements(data.items);
      setTotal(data.total);
      setSelectedRowKeys([]); // 清空选择
    } catch (error) {
      message.error("加载需求列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequirements();
  }, [page, pageSize, searchText]);

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) return;

    modal.confirm({
      title: "确认批量删除",
      content: `确定要删除选中的 ${selectedRowKeys.length} 个需求吗？`,
      onOk: async () => {
        try {
          await batchDeleteRequirements(selectedRowKeys as string[]);
          message.success("批量删除成功");
          loadRequirements();
        } catch (error) {
          // 全局错误处理器已显示详细错误消息
        }
      },
    });
  };

  // 删除需求
  const handleDelete = (id: string) => {
    modal.confirm({
      title: "确认删除",
      content: "确定要删除这个需求吗？",
      onOk: async () => {
        try {
          await deleteRequirement(id);
          message.success("删除成功");
          setRequirements((prev) => prev.filter((item) => item.id !== id));
          setTotal((prev) => prev - 1);
        } catch (error) {
          // 全局错误处理器已显示详细错误消息
        }
      },
    });
  };

  // 上传文件
  const handleUpload = (file: File) => {
    modal.confirm({
      title: "确认上传",
      content: `确定要上传文件 "${file.name}" 吗？`,
      onOk: async () => {
        setUploading(true);
        try {
          await uploadRequirement(file);
          message.success("上传成功");
          loadRequirements();
        } catch (error) {
          message.error("上传失败");
        } finally {
          setUploading(false);
        }
      }
    });
    return false; // 阻止默认上传行为
  };

  // 表格列定义
  const columns: ColumnsType<Requirement> = [
    {
      title: "ID",
      dataIndex: "seq_id",
      key: "seq_id",
      width: 80,
      render: (seq_id: number) => seq_id || "-",
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      render: (text: string, record: Requirement) => (
        <a onClick={() => navigate(`/requirements/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "版本",
      dataIndex: "version",
      key: "version",
      width: 100,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
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
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/requirements/${record.id}`)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/requirements/${record.id}/edit`)}
          >
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
    <div style={{ padding: 24 }}>
      {contextHolder}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <Space>
          <Search
            placeholder="搜索需求"
            allowClear
            onSearch={setSearchText}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          {selectedRowKeys.length > 0 && (
            <Button danger onClick={handleBatchDelete}>
              批量删除 ({selectedRowKeys.length})
            </Button>
          )}
        </Space>
        <Space>
          <Upload
            accept=".pdf,.docx,.doc,.md,.txt"
            beforeUpload={handleUpload}
            showUploadList={false}
          >
            <Button icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
          </Upload>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/requirements/new")}
          >
            新建需求
          </Button>
        </Space>
      </div>

      <Table
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        columns={columns}
        dataSource={requirements}
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
    </div>
  );
};

export default RequirementsPage;
