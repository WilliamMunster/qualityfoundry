/**
 * 报告详情页面
 */
import React from 'react';
import { Card, Descriptions, Tag } from 'antd';
import { useParams } from 'react-router-dom';

const ReportDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();

    return (
        <div>
            <Card title="报告详情">
                <Descriptions column={2} bordered>
                    <Descriptions.Item label="报告ID">{id}</Descriptions.Item>
                    <Descriptions.Item label="执行状态">
                        <Tag color="green">成功</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="执行时间">2026-01-09 22:00:00</Descriptions.Item>
                    <Descriptions.Item label="执行时长">5分30秒</Descriptions.Item>
                </Descriptions>
            </Card>
        </div>
    );
};

export default ReportDetailPage;
