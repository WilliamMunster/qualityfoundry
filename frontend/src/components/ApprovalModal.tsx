/**
 * 通用审核组件
 */
import React, { useState } from 'react';
import { Modal, Form, Input, Button, message } from 'antd';

interface ApprovalModalProps {
    visible: boolean;
    title: string;
    onApprove: (reviewer: string, comment?: string) => Promise<void>;
    onReject: (reviewer: string, comment?: string) => Promise<void>;
    onCancel: () => void;
}

const ApprovalModal: React.FC<ApprovalModalProps> = ({
    visible,
    title,
    onApprove,
    onReject,
    onCancel,
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);

    const handleApprove = async () => {
        try {
            const values = await form.validateFields();
            setLoading(true);
            await onApprove(values.reviewer, values.comment);
            message.success('审核通过');
            form.resetFields();
            onCancel();
        } catch (error) {
            message.error('审核失败');
        } finally {
            setLoading(false);
        }
    };

    const handleReject = async () => {
        try {
            const values = await form.validateFields();
            setLoading(true);
            await onReject(values.reviewer, values.comment);
            message.success('已拒绝');
            form.resetFields();
            onCancel();
        } catch (error) {
            message.error('操作失败');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal
            title={title}
            open={visible}
            onCancel={onCancel}
            footer={[
                <Button key="cancel" onClick={onCancel}>
                    取消
                </Button>,
                <Button key="reject" danger onClick={handleReject} loading={loading}>
                    拒绝
                </Button>,
                <Button key="approve" type="primary" onClick={handleApprove} loading={loading}>
                    通过
                </Button>,
            ]}
        >
            <Form form={form} layout="vertical">
                <Form.Item
                    name="reviewer"
                    label="审核人"
                    rules={[{ required: true, message: '请输入审核人' }]}
                >
                    <Input placeholder="请输入审核人姓名" />
                </Form.Item>
                <Form.Item name="comment" label="审核意见">
                    <Input.TextArea rows={4} placeholder="请输入审核意见（可选）" />
                </Form.Item>
            </Form>
        </Modal>
    );
};

export default ApprovalModal;
