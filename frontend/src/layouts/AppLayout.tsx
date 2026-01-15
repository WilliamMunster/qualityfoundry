/**
 * 主应用布局
 *
 * 明亮极简风格布局
 */
import React from "react";
import { Button, Layout, Menu, message, Typography } from "antd";
import {
  FileTextOutlined,
  BranchesOutlined,
  CheckSquareOutlined,
  CloudServerOutlined,
  PlayCircleOutlined,
  UserOutlined,
  LogoutOutlined,
  DashboardOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    message.success("已退出登录");
    navigate("/login");
  };

  const menuItems = [
    {
      key: "/report-dashboard",
      icon: <DashboardOutlined />,
      label: "测试报表",
    },
    {
      key: "/requirements",
      icon: <FileTextOutlined />,
      label: "需求管理",
    },
    {
      key: "/scenarios",
      icon: <BranchesOutlined />,
      label: "场景管理",
    },
    {
      key: "/testcases",
      icon: <CheckSquareOutlined />,
      label: "用例管理",
    },
    {
      key: "/environments",
      icon: <CloudServerOutlined />,
      label: "环境管理",
    },
    {
      key: "/executions",
      icon: <PlayCircleOutlined />,
      label: "执行管理",
    },
    {
      key: "/users",
      icon: <UserOutlined />,
      label: "用户管理",
    },
    {
      key: "/config-center",
      icon: <SettingOutlined />,
      label: "配置中心",
    },
  ];

  const username = JSON.parse(
    localStorage.getItem("user") || '{"username": "Guest"}'
  ).username;

  // 计算当前选中的菜单项
  const activeMenuKey = menuItems.find(item => 
    location.pathname === item.key || location.pathname.startsWith(`${item.key}/`)
  )?.key || location.pathname;

  return (
    <Layout style={{ minHeight: "100vh", background: "#F8F9FA" }}>
      {/* 顶部导航 */}
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 32px",
          background: "#FFFFFF",
          borderBottom: "1px solid #E8EAED",
          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
          }}
          onClick={() => navigate("/report-dashboard")}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, #4285F4, #1a73e8)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            Q
          </div>
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#202124",
              letterSpacing: "-0.5px",
            }}
          >
            QualityFoundry
          </span>
        </div>

        <div style={{ flex: 1 }} />

        {/* 用户信息 */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Text style={{ color: "#5F6368" }}>
            你好,{" "}
            <Text strong style={{ color: "#202124" }}>
              {username}
            </Text>
          </Text>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            style={{
              color: "#5F6368",
              borderRadius: 20,
            }}
          >
            退出
          </Button>
        </div>
      </Header>

      <Layout>
        {/* 侧边栏 */}
        <Sider
          width={220}
          style={{
            background: "#FFFFFF",
            borderRight: "1px solid #E8EAED",
            paddingTop: 16,
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[activeMenuKey]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{
              border: "none",
              background: "transparent",
            }}
          />
        </Sider>

        {/* 主内容区 */}
        <Layout style={{ padding: 24, background: "#F8F9FA" }}>
          <Content
            className="page-container"
            style={{
              padding: 24,
              background: "#FFFFFF",
              borderRadius: 16,
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              minHeight: 280,
            }}
          >
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
