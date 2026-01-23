import React from 'react';
import { Steps, Card, Space, Typography } from 'antd';
import { Bot, FileCode, Play, CheckCircle2, Loader2 } from 'lucide-react';

const { Text } = Typography;

interface NodeProgressProps {
    currentStatus?: string; // e.g., 'POLICY_LOADED', 'PLAN_BUILT', 'EXECUTING', 'DECIDING', 'FINISHED'
    error?: boolean;
}

const NodeProgress: React.FC<NodeProgressProps> = ({ currentStatus, error }) => {
    const statusMap: Record<string, number> = {
        'POLICY_LOADED': 0,
        'PLAN_BUILT': 1,
        'EXECUTING': 2,
        'DECIDING': 3,
        'FINISHED': 4,
    };

    const currentStep = statusMap[currentStatus || ''] ?? -1;

    const steps = [
        {
            title: '策略加载',
            description: '加载治理规则',
            icon: currentStep === 0 ? <Loader2 size={16} className="animate-spin text-blue-500" /> : <Bot size={16} />,
        },
        {
            title: '构建计划',
            description: 'AI 规划路径',
            icon: currentStep === 1 ? <Loader2 size={16} className="animate-spin text-blue-500" /> : <FileCode size={16} />,
        },
        {
            title: '工具执行',
            description: '运行测试脚本',
            icon: currentStep === 2 ? <Loader2 size={16} className="animate-spin text-blue-500" /> : <Play size={16} />,
        },
        {
            title: '证据评审',
            description: 'AI 辅助决策',
            icon: currentStep === 3 ? <Loader2 size={16} className="animate-spin text-blue-500" /> : <CheckCircle2 size={16} />,
        }
    ];

    return (
        <Card variant="borderless" style={{ background: '#F8FAFC', borderRadius: 16 }}>
            <Steps
                current={currentStep}
                status={error ? 'error' : 'process'}
                items={steps}
                size="small"
            />
        </Card>
    );
};

export default NodeProgress;
