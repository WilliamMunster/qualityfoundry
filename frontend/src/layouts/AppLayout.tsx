/**
 * 主应用布局
 */
import React from "react";
import { Button, Layout, Menu, message } from "antd";
import {
  FileTextOutlined,
  BranchesOutlined,
  CheckSquareOutlined,
  CloudServerOutlined,
  PlayCircleOutlined,
  UserOutlined,
  ThunderboltOutlined,
  LogoutOutlined,
  DashboardOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;

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
      key: "/ai-configs",
      icon: <ThunderboltOutlined />,
      label: "AI 配置",
    },
    {
      key: "/config-center",
      icon: <SettingOutlined />,
      label: "配置中心",
    },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{ display: "flex", alignItems: "center", padding: "0 24px" }}
      >
        <div style={{ color: "white", fontSize: 20, fontWeight: "bold" }}>
          QualityFoundry
        </div>
        <div style={{ flex: 1 }} />
        {/* Default to system user if not found, though login should enforce it */}
        <div style={{ color: "white", marginRight: 16 }}>
          你好,{" "}
          {
            JSON.parse(localStorage.getItem("user") || '{"username": "Guest"}')
              .username
          }
        </div>
        <Button
          type="text"
          icon={<LogoutOutlined />}
          style={{ color: "white" }}
          onClick={handleLogout}
        >
          退出
        </Button>
      </Header>

      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: "100%", borderRight: 0 }}
          />
        </Sider>

        <Layout style={{ padding: "0 24px 24px" }}>
          <Content
            style={{
              padding: 24,
              margin: 0,
              minHeight: 280,
              background: "#fff",
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
