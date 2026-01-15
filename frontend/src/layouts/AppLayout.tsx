/**
 * 主应用布局
 *
 * 明亮极简风格布局
 */
import React, { useMemo, useState } from "react";
import { Button, Layout, Menu, message, Typography, Breadcrumb, Avatar, Dropdown } from "antd";
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
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined
} from "@ant-design/icons";
import { Outlet, useNavigate, useLocation, Link } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

// 路由名称映射
const routeNameMap: Record<string, string> = {
  "report-dashboard": "测试报表",
  requirements: "需求管理",
  new: "新建",
  edit: "编辑",
  scenarios: "场景管理",
  testcases: "用例管理",
  environments: "环境管理",
  executions: "执行管理",
  users: "用户管理",
  "config-center": "配置中心",
};

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

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

  // 生成面包屑
  const breadcrumbItems = useMemo(() => {
    const pathSnippets = location.pathname.split("/").filter((i) => i);
    
    const items: { title: React.ReactNode }[] = [
      {
        title: <Link to="/"><HomeOutlined /></Link>,
      }
    ];

    pathSnippets.forEach((snippet, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join("/")}`;
      
      // 如果是ID（简单的判断：包含数字或长度很长），不显示或显示为"详情"
      let title = routeNameMap[snippet] || snippet;
      if (snippet.match(/^\d+$/) || snippet.length > 20) {
        title = "详情";
      }

      const isLast = index === pathSnippets.length - 1;
      
      items.push({
        title: isLast ? title : <Link to={url}>{title}</Link>,
      });
    });

    return items;
  }, [location]);

  const userMenu = {
    items: [
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        onClick: handleLogout
      }
    ]
  };

  return (
    <Layout style={{ minHeight: "100vh", background: "#F8F9FA" }}>
      {/* 顶部导航 */}
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 24px",
          background: "#FFFFFF",
          borderBottom: "1px solid #E8EAED",
          boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
          position: "sticky",
          top: 0,
          zIndex: 100,
          height: 64
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
            width: collapsed ? 80 : 220,
            transition: "all 0.2s"
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
              flexShrink: 0
            }}
          >
            Q
          </div>
          {!collapsed && (
            <span
              style={{
                fontSize: 18,
                fontWeight: 600,
                color: "#202124",
                letterSpacing: "-0.5px",
                whiteSpace: "nowrap",
                overflow: "hidden"
              }}
            >
              QualityFoundry
            </span>
          )}
        </div>

        <Button 
          type="text" 
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} 
          onClick={() => setCollapsed(!collapsed)}
          style={{ fontSize: '16px', width: 48, height: 48, marginRight: 16 }}
        />

        <div style={{ flex: 1 }} />

        {/* 用户信息 */}
        <Dropdown menu={userMenu} placement="bottomRight" arrow>
          <div style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 8, transition: "background 0.3s" }} className="user-dropdown">
            <Avatar style={{ backgroundColor: '#4285F4' }} icon={<UserOutlined />} />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
              <Text strong style={{ color: "#202124", fontSize: 14 }}>
                {username}
              </Text>
              <Text style={{ color: "#5F6368", fontSize: 11 }}>
                管理员
              </Text>
            </div>
          </div>
        </Dropdown>
      </Header>

      <Layout>
        {/* 侧边栏 */}
        <Sider
          trigger={null}
          collapsible 
          collapsed={collapsed}
          width={240}
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
        <Layout style={{ padding: "0 24px 24px", background: "#F8F9FA" }}>
          {/* 面包屑 */}
          <div style={{ margin: "16px 0" }}>
            <Breadcrumb items={breadcrumbItems} />
          </div>

          <Content
            className="page-container"
            style={{
              padding: 24,
              background: "#FFFFFF",
              borderRadius: 16,
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              minHeight: 280,
              overflow: "hidden"
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
