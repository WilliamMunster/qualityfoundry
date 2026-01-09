/**
 * 场景生成页面
 */
import React, { useState, useEffect } from 'react';
import { Card, Form, Select, Button, message, Spin, List } from 'antd';
import { useNavigate } from 'react-router-dom';
import { getRequirements, type Requirement } from '../api/requirements';
import { generateScenarios, type Scenario } from '../api/scenarios';

const ScenarioGeneratePage: React.FC = () => {
    const navigate = useNavigate();
    const [form] = Form.useForm();
    const [requirements, setRequirements] = useState<Requirement[]>([]);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [generatedScenarios, setGeneratedScenarios] = useState<Scenario[]>([]);

    useEffect(() => {
        loadRequirements();
    }, []);

    const loadRequirements = async () => {
        setLoading(true);
        try {
            const data = await getRequirements();
            setRequirements(data.items);
        } catch (error) {
            message.error('加载需求列表失败');
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async (values: any) => {
        setGenerating(true);
        try {
            const scenarios = await generateScenarios({
                requirement_id: values.requirement_id,
                auto_approve: values.auto_approve || false,
            });
            setGeneratedScenarios(scenarios);
            message.success(`成功生成 ${scenarios.length} 个场景`);
        } catch (error) {
            message.error('生成场景失败');
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div>
            <Card title="AI 生成测试场景">
                <Form form={form} layout="vertical" onFinish={handleGenerate}>
                    <Form.Item
                        name="requirement_id"
                        label="选择需求"
                        rules={[{ required: true, message: '请选择需求' }]}
                    >
                        <Select
                            placeholder="请选择需求"
                            loading={loading}
                            options={requirements.map(req => ({
                                label: req.title,
                                value: req.id,
                            }))}
                        />
                    </Form.Item>

                    <Form.Item name="auto_approve" label="自动审核" valuePropName="checked">
                        <Select
                            options={[
                                { label: '是', value: true },
                                { label: '否', value: false },
                            ]}
                        />
                    </Form.Item>

                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={generating}>
                            生成场景
                        </Button>
                    </Form.Item>
                </Form>

                {generating && (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                        <Spin size="large" />
                        <p style={{ marginTop: 16 }}>AI 正在生成测试场景...</p>
                    </div>
                )}

                {generatedScenarios.length > 0 && (
                    <Card title="生成结果" style={{ marginTop: 24 }}>
                        <List
                            dataSource={generatedScenarios}
                            renderItem={scenario => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={scenario.title}
                                        description={`${scenario.steps.length} 个步骤`}
                                    />
                                    <Button onClick={() => navigate(`/scenarios/${scenario.id}`)}>
                                        查看详情
                                    </Button>
                                </List.Item>
                            )}
                        />
                    </Card>
                )}
            </Card>
        </div>
    );
};

export default ScenarioGeneratePage;
