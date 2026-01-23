import React from 'react';
import { Typography } from 'antd';

const PoliciesPage: React.FC = () => {
    return (
        <div>
            <Typography.Title level={2}>策略库</Typography.Title>
            <p>展示当前加载的 Policy 内容 (只读)。</p>
        </div>
    );
};

export default PoliciesPage;
