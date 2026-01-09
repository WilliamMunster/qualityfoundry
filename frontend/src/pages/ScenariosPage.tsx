/**
 * 场景列表页面
 */
import React, { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

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
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);

  const columns: ColumnsType<Scenario> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      ellipsis: true,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '步骤数',
      dataIndex: 'steps',
      key: 'steps',
      width: 100,
      render: (steps: string[]) => steps.length,
    },
    {
      title: '审核状态',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'orange',
          approved: 'green',
          rejected: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: () => (
        <Space size="small">
          <Button type="link" size="small">查看</Button>
          <Button type="link" size="small">生成用例</Button>
          <Button type="link" size="small">审核</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>场景管理</h2>
        <Button type="primary" icon={<PlusOutlined />}>
          AI 生成场景
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={scenarios}
        rowKey="id"
        loading={loading}
      />
    </div>
  );
};

export default ScenariosPage;
