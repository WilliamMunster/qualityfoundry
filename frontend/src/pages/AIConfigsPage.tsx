/**
 * AI 配置管理页面
 */
import React, { useEffect, useState } from 'react';
import { Table, Button, Space, Tag, message, Modal, Form, Input, Select, Switch, Card } from 'antd';
import { PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import axios from 'axios';

interface AIConfig {
    id: string;
    name: string;
    provider: string;
    model: string;
    base_url?: string;
    assigned_steps?: string[];
    temperature: string;
    max_tokens: string;
    is_active: boolean;
    is_default: boolean;
    created_at: string;
}

const AIConfigsPage: React.FC = () => {
    const [configs, setConfigs] = useState<AIConfig[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [testModalVisible, setTestModalVisible] = useState(false);
    const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
    const [form] = Form.useForm();
    const [testForm] = Form.useForm();

    const stepOptions = [
        { label: '需求分析（需求→场景）', value: 'requirement_analysis' },
        { label: '场景生成', value: 'scenario_generation' },
        { label: '用例生成（场景→用例）', value: 'testcase_generation' },
        { label: '代码生成', value: 'code_generation' },
        { label: '审核建议', value: 'review' },
    ];

    const providerOptions = [
        { label: 'OpenAI', value: 'openai' },
        { label: 'DeepSeek', value: 'deepseek' },
        { label: 'Anthropic', value: 'anthropic' },
        { label: '其他', value: 'other' },
    ];

    useEffect(() => {
        loadConfigs();
    }, []);

    const loadConfigs = async () => {
        setLoading(true);
        try {
            const response = await axios.get('http://localhost:8000/api/v1/ai-configs');
            setConfigs(response.data);
        } catch (error) {
            message.error('加载配置列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (values: any) => {
        try {
            await axios.post('http://localhost:8000/api/v1/ai-configs', values);
            message.success('创建成功');
            setModalVisible(false);
            form.resetFields();
            loadConfigs();
        } catch (error) {
            message.error('创建失败');
        }
    };

    const handleTest = async (values: any) => {
        try {
            const response = await axios.post('http://localhost:8000/api/v1/ai-configs/test', {
                config_id: selectedConfig,
                prompt: values.prompt,
            });

            if (response.data.success) {
                message.success('测试成功');
                Modal.info({
                    title: 'AI 响应',
                    content: response.data.response,
                    width: 600,
                });
            } else {
                message.error(`测试失败: ${response.data.error}`);
            }
        } catch (error) {
            message.error('测试失败');
        }
    };

    const handleDelete = (id: string) => {
        Modal.confirm({
            title: '确认删除',
            content: '确定要删除这个配置吗？',
            onOk: async () => {
                try {
                    await axios.delete(`http://localhost:8000/api/v1/ai-configs/${id}`);
                    message.success('删除成功');
                    loadConfigs();
                } catch (error) {
                    message.error('删除失败');
                }
            },
        });
    };

    const columns: ColumnsType<AIConfig> = [
        { title: '配置名称', dataIndex: 'name', key: 'name' },
        {
            title: '提供商',
            dataIndex: 'provider',
            key: 'provider',
            render: (provider: string) => <Tag color="blue">{provider}</Tag>,
        },
        { title: '模型', dataIndex: 'model', key: 'model' },
        {
            title: '绑定步骤',
            dataIndex: 'assigned_steps',
            key: 'assigned_steps',
            render: (steps: string[]) => (
                <div>
                    {steps?.map(step => (
                        <Tag key={step} color="green" style={{ marginBottom: 4 }}>
                            {stepOptions.find(s => s.value === step)?.label || step}
                        </Tag>
                    ))}
                </div>
            ),
        },
        {
            title: '状态',
            key: 'status',
            render: (_, record) => (
                <Space>
                    {record.is_default && <Tag color="gold">默认</Tag>}
                    <Tag color={record.is_active ? 'green' : 'default'}>
                        {record.is_active ? '激活' : '禁用'}
                    </Tag>
                </Space>
            ),
        },
        {
            title: '操作',
            key: 'action',
            render: (_, record) => (
                <Space size="small">
                    <Button
                        type="link"
                        size="small"
                        icon={<ThunderboltOutlined />}
                        onClick={() => {
                            setSelectedConfig(record.id);
                            setTestModalVisible(true);
                        }}
                    >
                        测试
                    </Button>
                    <Button type="link" size="small">编辑</Button>
                    <Button type="link" size="small" danger onClick={() => handleDelete(record.id)}>
                        删除
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div>
            <Card
                title="AI 模型配置"
                extra={
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
                        新建配置
                    </Button>
                }
            >
                <Table columns={columns} dataSource={configs} rowKey="id" loading={loading} />
            </Card>

            <Modal
                title="新建 AI 配置"
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
                width={700}
            >
                <Form form={form} layout="vertical" onFinish={handleCreate}>
                    <Form.Item name="name" label="配置名称" rules={[{ required: true }]}>
                        <Input placeholder="例如：DeepSeek 需求分析" />
                    </Form.Item>

                    <Form.Item name="provider" label="提供商" rules={[{ required: true }]}>
                        <Select options={providerOptions} />
                    </Form.Item>

                    <Form.Item name="model" label="模型名称" rules={[{ required: true }]}>
                        <Input placeholder="例如：gpt-4, deepseek-chat" />
                    </Form.Item>

                    <Form.Item name="api_key" label="API Key" rules={[{ required: true }]}>
                        <Input.Password placeholder="输入 API Key" />
                    </Form.Item>

                    <Form.Item name="base_url" label="Base URL">
                        <Input placeholder="留空使用默认 URL" />
                    </Form.Item>

                    <Form.Item name="assigned_steps" label="绑定步骤">
                        <Select mode="multiple" options={stepOptions} placeholder="选择该模型执行的步骤" />
                    </Form.Item>

                    <Form.Item name="temperature" label="Temperature" initialValue="0.7">
                        <Input />
                    </Form.Item>

                    <Form.Item name="max_tokens" label="Max Tokens" initialValue="2000">
                        <Input />
                    </Form.Item>

                    <Form.Item name="is_default" label="设为默认" valuePropName="checked">
                        <Switch />
                    </Form.Item>
                </Form>
            </Modal>

            <Modal
                title="测试 AI 配置"
                open={testModalVisible}
                onCancel={() => setTestModalVisible(false)}
                onOk={() => testForm.submit()}
            >
                <Form form={testForm} layout="vertical" onFinish={handleTest}>
                    <Form.Item name="prompt" label="测试提示词" rules={[{ required: true }]}>
                        <Input.TextArea rows={4} placeholder="输入测试提示词，例如：你好，请介绍一下你自己" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default AIConfigsPage;
