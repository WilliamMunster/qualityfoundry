/**
 * 主应用布局
 *
 * 明亮极简风格布局
 */
import React, { useMemo, useState } from "react";
import { Button, Layout, Menu, message, Typography, Breadcrumb, Avatar, Dropdown } from "antd";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard,
  Eye,
  FileText,
  GitBranch,
  ShieldCheck,
  Box,
  PlayCircle,
  Users,
  Settings,
  Bot,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
  User,
  Home
} from "lucide-react";
import { Outlet, useNavigate, useLocation, Link } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

// 路由名称映射
const routeNameMap: Record<string, string> = {
  runs: "执行中心",
  new: "新建运行",
  id: "运行详情",
  policies: "策略库",
  regression: "回归报告",
  "report-dashboard": "测试报表",
  observer: "上帝视角",
  requirements: "需求管理",
  scenarios: "场景管理",
  testcases: "用例管理",
  environments: "环境管理",
  executions: "历史执行",
  users: "用户管理",
  "config-center": "配置中心",
  "ai-logs": "AI 调用日志",
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
      key: "/runs",
      icon: <PlayCircle size={18} />,
      label: "执行中心",
    },
    {
      key: "/policies",
      icon: <ShieldCheck size={18} />,
      label: "策略库",
    },
    {
      key: "/regression",
      icon: <LayoutDashboard size={18} />,
      label: "回归报告",
    },
    {
      type: 'divider' as const,
    },
    {
      key: "/report-dashboard",
      icon: <LayoutDashboard size={18} />,
      label: "数据驾驶舱",
    },
    {
      key: "/observer",
      icon: <Eye size={18} />,
      label: "上帝视角",
    },
    {
      key: "/requirements",
      icon: <FileText size={18} />,
      label: "需求管理",
    },
    {
      key: "/scenarios",
      icon: <GitBranch size={18} />,
      label: "场景管理",
    },
    {
      key: "/testcases",
      icon: <ShieldCheck size={18} />,
      label: "用例管理",
    },
    {
      key: "/environments",
      icon: <Box size={18} />,
      label: "环境管理",
    },
    {
      key: "/users",
      icon: <Users size={18} />,
      label: "用户管理",
    },
    {
      key: "/config-center",
      icon: <Settings size={18} />,
      label: "配置中心",
    },
    {
      key: "/ai-logs",
      icon: <Bot size={18} />,
      label: "AI 日志",
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
        title: <Link to="/"><Home size={14} /></Link>,
      }
    ];

    pathSnippets.forEach((snippet, index) => {
      const url = `/${pathSnippets.slice(0, index + 1).join("/")}`;

      // 如果是ID（简单的判断：包含数字或长度很长），不显示或显示为"详情"
      let title = routeNameMap[snippet] || snippet;
      if (snippet.match(/^\d+$/) || snippet.length > 20) {
        title = "分析详情";
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
        icon: <LogOut size={16} />,
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
          icon={collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
          onClick={() => setCollapsed(!collapsed)}
          style={{ width: 48, height: 48, marginRight: 16 }}
        />

        <div style={{ flex: 1 }} />

        {/* 用户信息 */}
        <Dropdown menu={userMenu} placement="bottomRight" arrow>
          <div style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer", padding: "4px 8px", borderRadius: 8, transition: "background 0.3s" }} className="user-dropdown">
            <Avatar style={{ backgroundColor: '#6366F1' }} icon={<User size={18} />} />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
              <Text strong style={{ color: "#1E293B", fontSize: 14 }}>
                {username}
              </Text>
              <Text style={{ color: "#64748B", fontSize: 11 }}>
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
              borderRadius: 20,
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              minHeight: 280,
              overflow: "hidden"
            }}
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
