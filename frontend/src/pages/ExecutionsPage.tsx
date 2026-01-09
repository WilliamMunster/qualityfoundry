/**
 * 执行管理页面
 */
import React, { useState } from 'react';
import { Table, Button, Space, Tag, Select } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

interface Execution {
  id: string;
  testcase_id: string;
  environment_id: string;
  mode: string;
  status: string;
  created_at: string;
}

const ExecutionsPage: React.FC = () => {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);

  const columns: ColumnsType<Execution> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      ellipsis: true,
    },
    {
      title: '执行模式',
      dataIndex: 'mode',
      key: 'mode',
      width: 120,
      render: (mode: string) => {
        const colorMap: Record<string, string> = {
          dsl: 'blue',
          mcp: 'green',
          hybrid: 'purple',
        };
        return <Tag color={colorMap[mode] || 'default'}>{mode.toUpperCase()}</Tag>;
      },
    },
    {
      title: '执行状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          success: 'success',
          failed: 'error',
          stopped: 'warning',
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
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small">查看详情</Button>
          <Button type="link" size="small">查看日志</Button>
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>执行管理</h2>
        <Space>
          <Select
            placeholder="选择环境"
            style={{ width: 150 }}
            options={[
              { value: 'dev', label: 'DEV' },
              { value: 'sit', label: 'SIT' },
              { value: 'uat', label: 'UAT' },
              { value: 'prod', label: 'PROD' },
            ]}
          />
          <Button type="primary" icon={<PlayCircleOutlined />}>
            新建执行
          </Button>
        </Space>
      </div>
      
      <Table
        columns={columns}
        dataSource={executions}
        rowKey="id"
        loading={loading}
      />
    </div>
  );
};

export default ExecutionsPage;
