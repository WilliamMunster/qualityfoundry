/**
 * 报告导出页面
 */
import React from 'react';
import { Card, Button, Space } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';

const ReportExportPage: React.FC = () => {
    return (
        <div>
            <Card title="导出测试报告">
                <Space direction="vertical" size="large">
                    <Button type="primary" icon={<DownloadOutlined />}>
                        导出为 PDF
                    </Button>
                    <Button icon={<DownloadOutlined />}>
                        导出为 Excel
                    </Button>
                    <Button icon={<DownloadOutlined />}>
                        导出为 HTML
                    </Button>
                </Space>
            </Card>
        </div>
    );
};

export default ReportExportPage;
