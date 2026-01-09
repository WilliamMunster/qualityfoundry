/**
 * 执行详情页面
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Button, Tag, Timeline, message } from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { getExecution, getExecutionLogs, type Execution } from '../api/executions';

const ExecutionDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [execution, setExecution] = useState<Execution | null>(null);
    const [logs, setLogs] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (id) {
            loadExecution(id);
            loadLogs(id);
        }
    }, [id]);

    const loadExecution = async (executionId: string) => {
        setLoading(true);
        try {
            const data = await getExecution(executionId);
            setExecution(data);
        } catch (error) {
            message.error('加载执行详情失败');
        } finally {
            setLoading(false);
        }
    };

    const loadLogs = async (executionId: string) => {
        try {
            const data = await getExecutionLogs(executionId);
            setLogs(data.logs || []);
        } catch (error) {
            console.error('加载日志失败');
        }
    };

    if (!execution) {
        return <div>加载中...</div>;
    }

    const statusColorMap: Record<string, string> = {
        pending: 'default',
        running: 'processing',
        success: 'success',
        failed: 'error',
        stopped: 'warning',
    };

    return (
        <div>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/executions')} style={{ marginBottom: 16 }}>
                返回列表
            </Button>

            <Card title="执行详情" loading={loading}>
                <Descriptions column={2} bordered>
                    <Descriptions.Item label="执行ID">{execution.id}</Descriptions.Item>
                    <Descriptions.Item label="执行模式">
                        <Tag>{execution.mode.toUpperCase()}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="执行状态">
                        <Tag color={statusColorMap[execution.status]}>{execution.status}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="用例ID">{execution.testcase_id}</Descriptions.Item>
                    <Descriptions.Item label="环境ID">{execution.environment_id}</Descriptions.Item>
                    <Descriptions.Item label="创建时间">
                        {new Date(execution.created_at).toLocaleString()}
                    </Descriptions.Item>
                    {execution.started_at && (
                        <Descriptions.Item label="开始时间">
                            {new Date(execution.started_at).toLocaleString()}
                        </Descriptions.Item>
                    )}
                    {execution.completed_at && (
                        <Descriptions.Item label="完成时间">
                            {new Date(execution.completed_at).toLocaleString()}
                        </Descriptions.Item>
                    )}
                    {execution.error_message && (
                        <Descriptions.Item label="错误信息" span={2}>
                            <span style={{ color: 'red' }}>{execution.error_message}</span>
                        </Descriptions.Item>
                    )}
                </Descriptions>

                {logs.length > 0 && (
                    <Card title="执行日志" style={{ marginTop: 24 }}>
                        <Timeline
                            items={logs.map((log: any) => ({
                                children: (
                                    <div>
                                        <div><strong>{log.level}</strong>: {log.message}</div>
                                        <div style={{ fontSize: 12, color: '#999' }}>
                                            {new Date(log.timestamp).toLocaleString()}
                                        </div>
                                    </div>
                                ),
                            }))}
                        />
                    </Card>
                )}
            </Card>
        </div>
    );
};

export default ExecutionDetailPage;
