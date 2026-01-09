/**
 * 主应用入口
 */
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import AppLayout from "./layouts/AppLayout";
import LoginPage from "./pages/LoginPage";
import RequirementsPage from "./pages/RequirementsPage";
import ScenariosPage from "./pages/ScenariosPage";
import TestCasesPage from "./pages/TestCasesPage";
import ExecutionsPage from "./pages/ExecutionsPage";
import EnvironmentsPage from "./pages/EnvironmentsPage";
import UsersPage from "./pages/UsersPage";
import AIConfigsPage from "./pages/AIConfigsPage";
import ReportDashboardPage from "./pages/ReportDashboardPage";

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<AppLayout />}>
            <Route
              index
              element={<Navigate to="/report-dashboard" replace />}
            />
            <Route path="requirements" element={<RequirementsPage />} />
            <Route path="scenarios" element={<ScenariosPage />} />
            <Route path="testcases" element={<TestCasesPage />} />
            <Route path="environments" element={<EnvironmentsPage />} />
            <Route path="executions" element={<ExecutionsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="ai-configs" element={<AIConfigsPage />} />
            <Route path="report-dashboard" element={<ReportDashboardPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
