import React, { useMemo } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    Edge,
    Node,
    Position,
    Handle,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Tag, Typography, Space } from 'antd';
import { Play, ShieldCheck, Wrench, CheckCircle2, ChevronRight, Bot } from 'lucide-react';

const { Text } = Typography;

// 自定义节点组件
const CustomNode = ({ data }: any) => {
    const Icon = data.icon || Play;
    const color = data.color || '#6366F1';

    return (
        <div style={{
            padding: '12px',
            borderRadius: '12px',
            background: '#fff',
            border: `2px solid ${color}`,
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            minWidth: '150px',
            textAlign: 'center'
        }}>
            <Handle type="target" position={Position.Top} style={{ background: color }} />
            <Space direction="vertical" size={1}>
                <div style={{ color: color, marginBottom: 4 }}>
                    <Icon size={20} />
                </div>
                <Text strong style={{ fontSize: '12px' }}>{data.label}</Text>
                {data.status && <Tag color={data.status === 'SUCCESS' ? 'success' : 'error'} style={{ margin: 0, fontSize: '10px' }}>{data.status}</Tag>}
            </Space>
            <Handle type="source" position={Position.Bottom} style={{ background: color }} />
        </div>
    );
};

const nodeTypes = {
    custom: CustomNode,
};

interface ExecutionFlowProps {
    events: any[];
}

const ExecutionFlow: React.FC<ExecutionFlowProps> = ({ events }) => {
    const { nodes, edges } = useMemo(() => {
        const nodes: Node[] = [];
        const edges: Edge[] = [];

        if (!events || events.length === 0) return { nodes, edges };

        // 提取关键节点：TOOL_STARTED, DECISION_MADE
        const keyEvents = events.filter(e =>
            ['TOOL_STARTED', 'DECISION_MADE', 'START_RUN', 'END_RUN'].includes(e.event_type) || e.node
        );

        let lastId = '';
        keyEvents.forEach((event, index) => {
            const id = event.id || `node-${index}`;
            let label = event.event_type;
            let icon = Play;
            let color = '#94A3B8';

            if (event.event_type === 'TOOL_STARTED') {
                label = `执行: ${event.tool_name || '工具'}`;
                icon = Wrench;
                color = '#6366F1';
            } else if (event.event_type === 'DECISION_MADE') {
                label = `决策: ${event.status || '结论'}`;
                icon = ShieldCheck;
                color = event.status === 'PASS' ? '#10B981' : '#EF4444';
            } else if (event.node) {
                label = `节点: ${event.node}`;
                icon = Bot;
                color = '#8B5CF6';
            }

            nodes.push({
                id,
                type: 'custom',
                position: { x: 250, y: index * 120 },
                data: { label, icon, color, status: event.status },
            });

            if (lastId) {
                edges.push({
                    id: `e-${lastId}-${id}`,
                    source: lastId,
                    target: id,
                    animated: true,
                    style: { stroke: '#CBD5E1' },
                });
            }
            lastId = id;
        });

        return { nodes, edges };
    }, [events]);

    return (
        <div style={{ height: '500px', width: '100%', background: '#F8FAFC', borderRadius: '16px', overflow: 'hidden' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                fitView
            >
                <Background gap={12} size={1} />
                <Controls />
            </ReactFlow>
        </div>
    );
};

export default ExecutionFlow;
