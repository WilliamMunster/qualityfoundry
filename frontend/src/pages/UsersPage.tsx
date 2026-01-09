/**
 * 用户管理页面
 */
import React, { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, message, Modal, Form, Input, Select } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';

interface User {
    id: string;
    username: string;
    email?: string;
    full_name?: string;
    role: string;
    is_active: boolean;
    created_at: string;
}

const UsersPage: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [form] = Form.useForm();

    useEffect(() => {
        loadUsers();
    }, []);

    const loadUsers = async () => {
        setLoading(true);
        try {
            const response = await axios.get('http://localhost:8000/api/v1/users');
            setUsers(response.data);
        } catch (error) {
            message.error('加载用户列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (values: any) => {
        try {
            await axios.post('http://localhost:8000/api/v1/users', values);
            message.success('创建成功');
            setModalVisible(false);
            form.resetFields();
            loadUsers();
        } catch (error) {
            message.error('创建失败');
        }
    };

    const handleDelete = (id: string) => {
        Modal.confirm({
            title: '确认删除',
            content: '确定要删除这个用户吗？',
            onOk: async () => {
                try {
                    await axios.delete(`http://localhost:8000/api/v1/users/${id}`);
                    message.success('删除成功');
                    loadUsers();
                } catch (error: any) {
                    message.error(error.response?.data?.detail || '删除失败');
                }
            },
        });
    };

    const columns: ColumnsType<User> = [
        { title: '用户名', dataIndex: 'username', key: 'username' },
        { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
        { title: '邮箱', dataIndex: 'email', key: 'email' },
        {
            title: '角色',
            dataIndex: 'role',
            key: 'role',
            render: (role: string) => (
                <Tag color={role === 'admin' ? 'red' : 'blue'}>{role}</Tag>
            ),
        },
        {
            title: '状态',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (active: boolean) => (
                <Tag color={active ? 'green' : 'default'}>{active ? '激活' : '禁用'}</Tag>
            ),
        },
        {
            title: '创建时间',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (text: string) => new Date(text).toLocaleString(),
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Space size="small">
                    <Button type="link" size="small">编辑</Button>
                    <Button
                        type="link"
                        size="small"
                        danger
                        onClick={() => handleDelete(record.id)}
                        disabled={record.username === 'admin'}
                    >
                        删除
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                <h2>用户管理</h2>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
                    新建用户
                </Button>
            </div>

            <Table columns={columns} dataSource={users} rowKey="id" loading={loading} />

            <Modal
                title="新建用户"
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
            >
                <Form form={form} layout="vertical" onFinish={handleCreate}>
                    <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                        <Input />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                        <Input.Password />
                    </Form.Item>
                    <Form.Item name="full_name" label="姓名">
                        <Input />
                    </Form.Item>
                    <Form.Item name="email" label="邮箱">
                        <Input type="email" />
                    </Form.Item>
                    <Form.Item name="role" label="角色" initialValue="user">
                        <Select>
                            <Select.Option value="admin">管理员</Select.Option>
                            <Select.Option value="user">用户</Select.Option>
                            <Select.Option value="viewer">查看者</Select.Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default UsersPage;
