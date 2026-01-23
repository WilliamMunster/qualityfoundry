import React, { useEffect, useState } from 'react';
import { Typography, Form, Input, Button, Select, Card, Space, Collapse, message } from 'antd';
import { Rocket, Settings, ChevronLeft, Globe, Terminal, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import orchestrationsApi from '../api/orchestrations';
import { getEnvironments, Environment } from '../api/environments';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

const RunLaunchPage: React.FC = () => {
    const navigate = useNavigate();
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [environments, setEnvironments] = useState<Environment[]>([]);

    useEffect(() => {
        const fetchEnvs = async () => {
            try {
                const res = await getEnvironments({ is_active: true });
                setEnvironments(res.items);
            } catch (error) {
                console.error('Failed to fetch environments:', error);
            }
        };
        fetchEnvs();
    }, []);

    const onFinish = async (values: any) => {
        setLoading(true);
        try {
            const payload = {
                nl_input: values.nl_input,
                environment_id: values.environment_id,
                options: values.use_options ? {
                    tool_name: values.tool_name,
                    args: values.args ? JSON.parse(values.args) : {},
                    timeout_s: values.timeout_s,
                    dry_run: values.dry_run,
                } : undefined
            };

            const res = await orchestrationsApi.run(payload);
            message.success('运行已启动');
            navigate(`/runs/${res.run_id}`);
        } catch (error: any) {
            console.error('Run failed:', error);
            // Error handled by interceptor
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: 800, margin: '0 auto', padding: '12px 0' }}>
            <Button
                type="text"
                icon={<ChevronLeft size={16} />}
                onClick={() => navigate('/runs')}
                style={{ marginBottom: 16 }}
            >
                返回列表
            </Button>

            <div style={{ marginBottom: 32 }}>
                <Title level={2}>
                    <Rocket size={24} style={{ marginRight: 12, verticalAlign: 'middle' }} className="text-blue-500" />
                    新建运行
                </Title>
                <Paragraph type="secondary">
                    请输入您的测试意图，支持自然语言。您可以直接描述“跑一下所有登录测试”，或在下方配置特定工具。
                </Paragraph>
            </div>

            <Form
                form={form}
                layout="vertical"
                initialValues={{
                    tool_name: 'run_pytest',
                    timeout_s: 120,
                    dry_run: false,
                    args: '{}'
                }}
                onFinish={onFinish}
            >
                <Card
                    variant="outlined"
                    style={{ borderRadius: 16, marginBottom: 24, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                >
                    <Form.Item
                        label="测试意图 (NL Input)"
                        name="nl_input"
                        rules={[{ required: true, message: '请输入测试描述' }]}
                    >
                        <TextArea
                            placeholder="例如：对 staging 环境运行 smoke 测试，确保核心流程通过"
                            rows={4}
                            style={{ borderRadius: 8 }}
                        />
                    </Form.Item>

                    <Form.Item
                        label="运行环境"
                        name="environment_id"
                        rules={[{ required: true, message: '请选择环境' }]}
                    >
                        <Select
                            placeholder="选择执行环境"
                            suffixIcon={<Globe size={16} />}
                            style={{ height: 40 }}
                        >
                            {environments.map(env => (
                                <Select.Option key={env.id} value={env.id}>{env.name}</Select.Option>
                            ))}
                        </Select>
                    </Form.Item>
                </Card>

                <Collapse
                    ghost
                    expandIconPosition="end"
                    style={{ marginBottom: 24 }}
                >
                    <Panel
                        header={
                            <Space>
                                <Settings size={16} className="text-gray-500" />
                                <Text strong>高级配置 (可选)</Text>
                            </Space>
                        }
                        key="options"
                    >
                        <Form.Item name="use_options" valuePropName="checked" noStyle>
                            <Input type="hidden" />
                        </Form.Item>

                        <div style={{ padding: '0 12px' }}>
                            <Form.Item label="指定工具" name="tool_name">
                                <Select>
                                    <Select.Option value="run_pytest">Pytest (单元/集成测试)</Select.Option>
                                    <Select.Option value="run_playwright">Playwright (浏览器端对端)</Select.Option>
                                </Select>
                            </Form.Item>

                            <Form.Item label="工具参数 (JSON)" name="args">
                                <TextArea
                                    placeholder='{"test_path": "tests/smoke"}'
                                    rows={3}
                                    style={{ fontFamily: 'monospace' }}
                                />
                            </Form.Item>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                                <Form.Item label="超时时间 (秒)" name="timeout_s">
                                    <Input type="number" suffix={<Terminal size={14} />} />
                                </Form.Item>
                                <Form.Item label="执行模式" name="dry_run">
                                    <Select>
                                        <Select.Option value={false}>真实执行</Select.Option>
                                        <Select.Option value={true}>干运行 (只解析不执行)</Select.Option>
                                    </Select>
                                </Form.Item>
                            </div>
                        </div>
                    </Panel>
                </Collapse>

                <Form.Item>
                    <Button
                        type="primary"
                        htmlType="submit"
                        loading={loading}
                        block
                        style={{ height: 48, borderRadius: 24, fontSize: 16, fontWeight: 600 }}
                    >
                        立即启动
                    </Button>
                </Form.Item>
            </Form>

            <Card style={{ background: '#F8F9FA', border: 'none', borderRadius: 12 }}>
                <Space align="start">
                    <ShieldAlert size={18} className="text-amber-500" style={{ marginTop: 2 }} />
                    <div>
                        <Text strong>安全警示：</Text>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                            系统将根据您的描述自动选择工具和参数。如果未开启“高级配置”，系统会基于 NLP 启发式策略决定执行方案。
                        </Text>
                    </div>
                </Space>
            </Card>
        </div>
    );
};

export default RunLaunchPage;
