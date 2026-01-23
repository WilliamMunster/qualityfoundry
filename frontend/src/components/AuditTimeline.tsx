import React from 'react';
import { Timeline, Tag, Typography, Space, Empty } from 'antd';
import { Clock, User, Terminal, CheckCircle2, AlertCircle } from 'lucide-react';
import dayjs from 'dayjs';

const { Text } = Typography;

interface AuditTimelineProps {
    events: any[];
    loading?: boolean;
}

const AuditTimeline: React.FC<AuditTimelineProps> = ({ events, loading }) => {
    if (!loading && (!events || events.length === 0)) {
        return <Empty description="暂无审计事件" />;
    }

    const getTimelineItem = (event: any) => {
        const isError = event.status === 'FAILED';
        const color = isError ? 'red' : 'green';

        return {
            color: color,
            children: (
                <div style={{ marginBottom: 16 }}>
                    <Space style={{ marginBottom: 4 }}>
                        <Text strong>{event.event_type}</Text>
                        <Tag color={color}>{event.status || 'INFO'}</Tag>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                            <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                            {dayjs(event.ts).format('HH:mm:ss.SSS')}
                        </Text>
                    </Space>
                    <div>
                        {event.node && <Tag icon={<Terminal size={10} />}>{event.node}</Tag>}
                        {event.tool_name && <Text type="secondary">工具: {event.tool_name}</Text>}
                    </div>
                    {event.details && (
                        <div style={{ marginTop: 8, padding: 8, background: '#f5f5f5', borderRadius: 4, fontSize: '12px' }}>
                            {event.details.message || JSON.stringify(event.details)}
                        </div>
                    )}
                </div>
            ),
            dot: isError ? <AlertCircle size={16} className="text-red-500" /> : <CheckCircle2 size={16} className="text-green-500" />,
        };
    };

    return (
        <Timeline
            pending={loading ? "加载审计流中..." : false}
            items={events.map(getTimelineItem)}
        />
    );
};

export default AuditTimeline;
