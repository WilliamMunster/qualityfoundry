/**
 * 场景详情页面
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Space, Tag, message, Steps } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { getScenario, type Scenario } from '../api/scenarios';

const ScenarioDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [scenario, setScenario] = useState<Scenario | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (id) {
            loadScenario(id);
        }
    }, [id]);

    const loadScenario = async (scenarioId: string) => {
        setLoading(true);
        try {
            const data = await getScenario(scenarioId);
            setScenario(data);
        } catch (error) {
            message.error('加载场景详情失败');
        } finally {
            setLoading(false);
        }
    };

    if (!scenario) {
        return <div>加载中...</div>;
    }

    return (
        <div>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/scenarios')} style={{ marginBottom: 16 }}>
                返回列表
            </Button>

            <Card title="场景详情" loading={loading}>
                <Descriptions column={2} bordered>
                    <Descriptions.Item label="ID">{scenario.id}</Descriptions.Item>
                    <Descriptions.Item label="标题">{scenario.title}</Descriptions.Item>
                    <Descriptions.Item label="需求ID">{scenario.requirement_id}</Descriptions.Item>
                    <Descriptions.Item label="审核状态">
                        <Tag color={scenario.approval_status === 'approved' ? 'green' : 'orange'}>
                            {scenario.approval_status}
                        </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="描述" span={2}>
                        {scenario.description || '无'}
                    </Descriptions.Item>
                    <Descriptions.Item label="创建时间" span={2}>
                        {new Date(scenario.created_at).toLocaleString()}
                    </Descriptions.Item>
                </Descriptions>

                <Card title="测试步骤" style={{ marginTop: 24 }}>
                    <Steps
                        direction="vertical"
                        current={-1}
                        items={scenario.steps.map((step, index) => ({
                            title: `步骤 ${index + 1}`,
                            description: step,
                        }))}
                    />
                </Card>
            </Card>
        </div>
    );
};

export default ScenarioDetailPage;
