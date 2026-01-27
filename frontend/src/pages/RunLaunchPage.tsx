import React, { useEffect, useState } from 'react';
import { Typography, Form, Input, Button, Select, Card, Space, Collapse, message } from 'antd';
import { Rocket, Settings, ChevronLeft, Globe, Terminal, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import orchestrationsApi from '../api/orchestrations';
import { getEnvironments, Environment } from '../api/environments';
import ReadinessCheck from '../components/ReadinessCheck';

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

            <ReadinessCheck />

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
                                    <Select.Option value="playwright">Pytest (UI: Playwright)</Select.Option>
                                </Select>
                            </Form.Item>

                            <Form.Item noStyle shouldUpdate={(prev, curr) => prev.tool_name !== curr.tool_name}>
                                {({ getFieldValue }) => {
                                    const tool = getFieldValue('tool_name');
                                    if (tool === 'playwright') {
                                        return (
                                            <div style={{ marginBottom: 16 }}>
                                                <div style={{ padding: '12px', background: '#e6f4ff', borderRadius: 8, border: '1px solid #91caff', marginBottom: 12 }}>
                                                    <Space align="start" style={{ marginBottom: 8 }}>
                                                        <Terminal size={14} className="text-blue-500" style={{ marginTop: 2 }} />
                                                        <Text strong style={{ fontSize: '14px' }}>我会发生什么 (Workflow)</Text>
                                                    </Space>
                                                    <div style={{ marginLeft: 22 }}>
                                                        <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                                                            1. <b>映射</b>：系统自动将请求路由至 <code>run_pytest</code> 工具。
                                                        </Text>
                                                        <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                                                            2. <b>执行</b>：在沙箱中运行 <code>tests/ui</code> 下标记为 playwright 的测试。
                                                        </Text>
                                                        <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                                                            3. <b>收集</b>：截图将自动从环境变量 <code>QUALITYFOUNDRY_ARTIFACT_DIR/ui</code> 中提取。
                                                        </Text>
                                                        <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
                                                            4. <b>展示</b>：详情页详情页 Evidence 标签页将实时预览截图。
                                                        </Text>
                                                    </div>
                                                </div>

                                                <div style={{ padding: '12px', background: '#fff7e6', borderRadius: 8, border: '1px solid #ffe58f' }}>
                                                    <Space align="start" style={{ marginBottom: 4 }}>
                                                        <ShieldAlert size={14} className="text-amber-500" style={{ marginTop: 2 }} />
                                                        <Text strong style={{ fontSize: '14px' }}>启动先决条件 (Pre-requisites)</Text>
                                                    </Space>
                                                    <div style={{ marginLeft: 22 }}>
                                                        <ul style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
                                                            <li><Text type="secondary" style={{ fontSize: '12px' }}>• <b>开关</b>：环境变量 <code>QF_ENABLE_UI_TESTS=1</code> 已开启</Text></li>
                                                            <li><Text type="secondary" style={{ fontSize: '12px' }}>• <b>浏览器</b>：Runner 已安装 Playwright Browsers</Text></li>
                                                            <li><Text type="secondary" style={{ fontSize: '12px' }}>• <b>策略</b>：当前 Governance Policy 允许 <code>run_pytest</code> 操作</Text></li>
                                                            <li><Text type="secondary" style={{ fontSize: '12px', color: '#d46b08' }}><i>注意：若缺失先决条件，系统将自动记录 Skip 证据以保持审计完整性。</i></Text></li>
                                                        </ul>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    }
                                    return null;
                                }}
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
