import React from 'react';
import { Typography } from 'antd';

const RegressionPage: React.FC = () => {
    return (
        <div>
            <Typography.Title level={2}>回归报告</Typography.Title>
            <p>展示回归评测的对比报告 (只读)。</p>
        </div>
    );
};

export default RegressionPage;
