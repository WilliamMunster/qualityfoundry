/**
 * 登录页面 - 明亮极简风格
 *
 * 基于 Google Antigravity 设计语言
 */
import React, { useState } from "react";
import { Form, Input, Button, Typography } from "antd";
import { message } from "../components/AntdGlobal";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";
import ParticleBackground from "../components/ParticleBackground";

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleLogin = async (values: {
    username: string;
    password: string;
  }) => {
    setLoading(true);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = await apiClient.post(
        "/api/v1/users/login",
        {
          username: values.username,
          password: values.password,
        }
      );

      // 保存 token 和用户信息
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));

      message.success("登录成功");
      navigate("/");
    } catch {
      // 错误已经由拦截器处理，或者是网络错误
      // 但为了保证 UI 状态正确，这里还是 catch 一下，虽然拦截器可能已经弹窗
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(180deg, #FFFFFF 0%, #F8F9FA 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 粒子背景 */}
      <ParticleBackground
        particleCount={60}
        color="#4285F4"
        minSize={2}
        maxSize={5}
        speed={0.2}
      />

      {/* 登录卡片 */}
      <div
        className="animate-fade-in-up"
        style={{
          width: 420,
          padding: 48,
          background: "rgba(255, 255, 255, 0.95)",
          borderRadius: 24,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.08)",
          backdropFilter: "blur(10px)",
          position: "relative",
          zIndex: 1,
        }}
      >
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: "linear-gradient(135deg, #4285F4, #1a73e8)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 20,
              boxShadow: "0 4px 16px rgba(66, 133, 244, 0.3)",
            }}
          >
            <span style={{ color: "white", fontSize: 28, fontWeight: 700 }}>
              Q
            </span>
          </div>
          <Title
            level={2}
            style={{ margin: 0, color: "#202124", fontWeight: 600 }}
          >
            QualityFoundry
          </Title>
          <Text style={{ color: "#5F6368", fontSize: 16 }}>
            企业级测试管理平台
          </Text>
        </div>

        {/* 登录表单 */}
        <Form
          name="login"
          onFinish={handleLogin}
          size="large"
          layout="vertical"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: "#9AA0A6" }} />}
              placeholder="用户名"
              style={{
                height: 48,
                borderRadius: 12,
                fontSize: 15,
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: "#9AA0A6" }} />}
              placeholder="密码"
              style={{
                height: 48,
                borderRadius: 12,
                fontSize: 15,
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginTop: 32, marginBottom: 16 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 48,
                borderRadius: 24,
                fontSize: 16,
                fontWeight: 500,
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        {/* 底部提示 */}
        <div style={{ textAlign: "center" }}>
          <Text style={{ color: "#9AA0A6", fontSize: 13 }}>
            默认管理员账号：admin / admin
          </Text>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
