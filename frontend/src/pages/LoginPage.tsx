/**
 * 登录页面 - 科技前卫风格
 */
import React, { useState } from 'react';
import { Form, Input, Button, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './LoginPage.css';

const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);

    const handleLogin = async (values: any) => {
        setLoading(true);
        try {
            const response = await axios.post('http://localhost:8000/api/v1/users/login', {
                username: values.username,
                password: values.password,
            });

            // 保存 token 和用户信息
            localStorage.setItem('token', response.data.access_token);
            localStorage.setItem('user', JSON.stringify(response.data.user));

            message.success('登录成功');
            navigate('/');
        } catch (error) {
            message.error('登录失败，请检查用户名和密码');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-background">
                <div className="tech-grid"></div>
                <div className="tech-particles"></div>
            </div>

            <div className="login-box">
                <div className="login-header">
                    <h1 className="login-title">QualityFoundry</h1>
                    <p className="login-subtitle">企业级测试管理平台</p>
                </div>

                <Form
                    name="login"
                    onFinish={handleLogin}
                    size="large"
                    className="login-form"
                >
                    <Form.Item
                        name="username"
                        rules={[{ required: true, message: '请输入用户名' }]}
                    >
                        <Input
                            prefix={<UserOutlined />}
                            placeholder="用户名"
                            className="login-input"
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: '请输入密码' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined />}
                            placeholder="密码"
                            className="login-input"
                        />
                    </Form.Item>

                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            className="login-button"
                            block
                        >
                            登录
                        </Button>
                    </Form.Item>
                </Form>

                <div className="login-footer">
                    <p>默认管理员账号：admin / admin</p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
