import React, { useState, useEffect } from "react";
import {
    Table,
    Card,
    Tag,
    Space,
    Typography,
    Button,
    Modal,
    Descriptions,
    Badge,
} from "antd";
import { message } from "../components/AntdGlobal";
import {
    RobotOutlined,
    EyeOutlined,
    ReloadOutlined,
} from "@ant-design/icons";
import { getAIExecutionLogs, AIExecutionLog } from "../api/ai-configs";

const { Title, Text, Paragraph } = Typography;

const STEP_NAMES: Record<string, string> = {
    requirement_analysis: "需求分析",
    scenario_generation: "场景生成",
    testcase_generation: "用例生成",
    code_generation: "代码生成",
    review: "审核建议",
    execution_analysis: "执行结果分析",
    global_observer: "上帝视角分析",
};

const AIExecutionLogsPage: React.FC = () => {
    const [logs, setLogs] = useState<AIExecutionLog[]>([]);
    const [loading, setLoading] = useState(false);
    const [detailVisible, setDetailVisible] = useState(false);
    const [selectedLog, setSelectedLog] = useState<AIExecutionLog | null>(null);

    const loadLogs = async () => {
        try {
            setLoading(true);
            const data: any = await getAIExecutionLogs({ limit: 100 });
            setLogs(data);
        } catch (error) {
            console.error("加载日志失败:", error);
            message.error("加载日志失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadLogs();
    }, []);

    const columns = [
        {
            title: "时间",
            dataIndex: "created_at",
            key: "created_at",
            render: (text: string) => new Date(text).toLocaleString(),
            width: 180,
        },
        {
            title: "步骤",
            dataIndex: "step",
            key: "step",
            render: (step: string) => <Tag color="blue">{STEP_NAMES[step] || step || "未知"}</Tag>,
        },
        {
            title: "模型",
            key: "model",
            render: (_: any, record: AIExecutionLog) => (
                <span>
                    <Tag color="geekblue">{record.provider?.toUpperCase()}</Tag>
                    <Text type="secondary">{record.model}</Text>
                </span>
            ),
        },
        {
            title: "状态",
            dataIndex: "status",
            key: "status",
            render: (status: string) => (
                <Badge
                    status={status === "success" ? "success" : "error"}
                    text={status === "success" ? "成功" : "失败"}
                />
            ),
        },
        {
            title: "耗时",
            dataIndex: "duration_ms",
            key: "duration_ms",
            render: (ms: number) => <span>{ms}ms</span>,
        },
        {
            title: "操作",
            key: "action",
            render: (_: any, record: AIExecutionLog) => (
                <Button
                    type="link"
                    icon={<EyeOutlined />}
                    onClick={() => {
                        setSelectedLog(record);
                        setDetailVisible(true);
                    }}
                >
                    查看详情
                </Button>
            ),
        },
    ];

    return (
        <div style={{ padding: "0" }}>
            <Title level={2}>
                <RobotOutlined /> AI 调用日志
            </Title>
            <Paragraph>
                查看 AI 模型的调用记录，包括请求详情、响应内容以及失败原因。
            </Paragraph>

            <Card>
                <div style={{ marginBottom: 16 }}>
                    <Button icon={<ReloadOutlined />} onClick={loadLogs} loading={loading}>
                        刷新日志
                    </Button>
                </div>
                <Table
                    dataSource={logs}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 20 }}
                />
            </Card>

            <Modal
                title="调用详情"
                open={detailVisible}
                onCancel={() => setDetailVisible(false)}
                width={800}
                footer={[
                    <Button key="close" onClick={() => setDetailVisible(false)}>
                        关闭
                    </Button>,
                ]}
            >
                {selectedLog && (
                    <Descriptions column={2} bordered>
                        <Descriptions.Item label="调用 ID" span={2}>
                            {selectedLog.id}
                        </Descriptions.Item>
                        <Descriptions.Item label="创建时间">
                            {new Date(selectedLog.created_at).toLocaleString()}
                        </Descriptions.Item>
                        <Descriptions.Item label="状态">
                            {selectedLog.status === "success" ? (
                                <Tag color="success">成功</Tag>
                            ) : (
                                <Tag color="error">失败</Tag>
                            )}
                        </Descriptions.Item>
                        <Descriptions.Item label="提供商">
                            {selectedLog.provider?.toUpperCase()}
                        </Descriptions.Item>
                        <Descriptions.Item label="模型">
                            {selectedLog.model}
                        </Descriptions.Item>
                        <Descriptions.Item label="耗时">
                            {selectedLog.duration_ms}ms
                        </Descriptions.Item>
                        <Descriptions.Item label="执行步骤">
                            {STEP_NAMES[selectedLog.step || ""] || selectedLog.step}
                        </Descriptions.Item>

                        {selectedLog.status === "failed" && (
                            <Descriptions.Item label="错误信息" span={2}>
                                <Text type="danger">{selectedLog.error_message}</Text>
                            </Descriptions.Item>
                        )}

                        <Descriptions.Item label="请求消息" span={2}>
                            <div
                                style={{
                                    background: "#f5f5f5",
                                    padding: 12,
                                    borderRadius: 4,
                                    maxHeight: 250,
                                    overflowY: "auto",
                                }}
                            >
                                <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                                    {JSON.stringify(selectedLog.request_messages, null, 2)}
                                </pre>
                            </div>
                        </Descriptions.Item>

                        <Descriptions.Item label="响应内容" span={2}>
                            <div
                                style={{
                                    background: "#f5f5f5",
                                    padding: 12,
                                    borderRadius: 4,
                                    maxHeight: 350,
                                    overflowY: "auto",
                                    whiteSpace: "pre-wrap",
                                    wordBreak: "break-all",
                                }}
                            >
                                {selectedLog.response_content || "无内容"}
                            </div>
                        </Descriptions.Item>
                    </Descriptions>
                )}
            </Modal>
        </div>
    );
};

export default AIExecutionLogsPage;
