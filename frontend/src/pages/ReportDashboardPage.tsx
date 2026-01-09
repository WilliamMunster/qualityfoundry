/**
 * 报告仪表板页面
 */
import React, { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Table } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import axios from "axios";

const ReportDashboardPage: React.FC = () => {
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failed: 0,
    running: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(
          "http://localhost:8000/api/v1/reports/dashboard-stats"
        );
        setStats(response.data);
      } catch (error) {
        console.error("Failed to fetch stats:", error);
      }
    };
    fetchStats();
  }, []);

  interface Execution {
    id: string;
    testcase: string;
    status: string;
    time: string;
  }

  const recentExecutions: Execution[] = [
    // TODO: 从 API 加载最近执行记录
  ];

  return (
    <div>
      <h2>测试报告仪表板</h2>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总执行次数"
              value={stats.total}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功"
              value={stats.success}
              valueStyle={{ color: "#3f8600" }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={stats.failed}
              valueStyle={{ color: "#cf1322" }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行中"
              value={stats.running}
              valueStyle={{ color: "#1890ff" }}
              prefix={<SyncOutlined spin={stats.running > 0} />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近执行记录" style={{ marginTop: 24 }}>
        <Table
          dataSource={recentExecutions}
          columns={[
            { title: "执行ID", dataIndex: "id", key: "id" },
            { title: "用例", dataIndex: "testcase", key: "testcase" },
            { title: "状态", dataIndex: "status", key: "status" },
            { title: "执行时间", dataIndex: "time", key: "time" },
          ]}
        />
      </Card>
    </div>
  );
};

export default ReportDashboardPage;
