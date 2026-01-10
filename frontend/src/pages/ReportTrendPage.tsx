/**
 * 报告趋势页面
 *
 * 展示执行趋势图表（按日期统计成功/失败数量）
 */
import React, { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Spin, Empty, Select, Space } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LineChartOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import axios from "axios";
import dayjs from "dayjs";

interface DailyStats {
  date: string;
  total: number;
  success: number;
  failed: number;
}

interface Execution {
  id: string;
  status: string;
  created_at: string;
}

const ReportTrendPage: React.FC = () => {
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadTrendData();
  }, [days]);

  const loadTrendData = async () => {
    setLoading(true);
    try {
      // 获取最近的执行记录
      const response = await axios.get("/api/v1/executions", {
        params: { page: 1, page_size: 500 },
      });
      const executions: Execution[] = response.data.items || [];

      // 按日期分组统计
      const statsMap: Record<string, DailyStats> = {};
      const today = dayjs();

      // 初始化最近 N 天的数据
      for (let i = days - 1; i >= 0; i--) {
        const date = today.subtract(i, "day").format("YYYY-MM-DD");
        statsMap[date] = { date, total: 0, success: 0, failed: 0 };
      }

      // 统计每天的数据
      executions.forEach((exec) => {
        const date = dayjs(exec.created_at).format("YYYY-MM-DD");
        if (statsMap[date]) {
          statsMap[date].total++;
          if (exec.status === "success") {
            statsMap[date].success++;
          } else if (exec.status === "failed") {
            statsMap[date].failed++;
          }
        }
      });

      // 转换为数组
      const statsArray = Object.values(statsMap).sort((a, b) =>
        a.date.localeCompare(b.date)
      );

      setDailyStats(statsArray);
    } catch (error) {
      console.error("加载趋势数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 计算总计
  const totalStats = dailyStats.reduce(
    (acc, day) => ({
      total: acc.total + day.total,
      success: acc.success + day.success,
      failed: acc.failed + day.failed,
    }),
    { total: 0, success: 0, failed: 0 }
  );

  // 计算成功率
  const successRate =
    totalStats.total > 0
      ? ((totalStats.success / totalStats.total) * 100).toFixed(1)
      : "0.0";

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2>
          <LineChartOutlined /> 测试趋势分析
        </h2>
        <Space>
          <span>时间范围：</span>
          <Select
            value={days}
            onChange={setDays}
            options={[
              { label: "最近 7 天", value: 7 },
              { label: "最近 14 天", value: 14 },
              { label: "最近 30 天", value: 30 },
            ]}
          />
        </Space>
      </div>

      {/* 汇总统计 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总执行次数" value={totalStats.total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功次数"
              value={totalStats.success}
              valueStyle={{ color: "#3f8600" }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败次数"
              value={totalStats.failed}
              valueStyle={{ color: "#cf1322" }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={successRate}
              suffix="%"
              valueStyle={{
                color: parseFloat(successRate) >= 80 ? "#3f8600" : "#cf1322",
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 每日趋势 */}
      <Card
        title={
          <>
            <BarChartOutlined /> 每日执行趋势
          </>
        }
      >
        {dailyStats.length === 0 ? (
          <Empty description="暂无数据" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #f0f0f0" }}>
                  <th style={{ padding: "12px 8px", textAlign: "left" }}>
                    日期
                  </th>
                  <th style={{ padding: "12px 8px", textAlign: "center" }}>
                    总计
                  </th>
                  <th style={{ padding: "12px 8px", textAlign: "center" }}>
                    成功
                  </th>
                  <th style={{ padding: "12px 8px", textAlign: "center" }}>
                    失败
                  </th>
                  <th
                    style={{
                      padding: "12px 8px",
                      textAlign: "left",
                      width: "40%",
                    }}
                  >
                    分布
                  </th>
                </tr>
              </thead>
              <tbody>
                {dailyStats.map((day) => {
                  const maxTotal = Math.max(
                    ...dailyStats.map((d) => d.total),
                    1
                  );
                  const successWidth = (day.success / maxTotal) * 100;
                  const failedWidth = (day.failed / maxTotal) * 100;

                  return (
                    <tr
                      key={day.date}
                      style={{ borderBottom: "1px solid #f0f0f0" }}
                    >
                      <td style={{ padding: "12px 8px" }}>{day.date}</td>
                      <td style={{ padding: "12px 8px", textAlign: "center" }}>
                        {day.total}
                      </td>
                      <td
                        style={{
                          padding: "12px 8px",
                          textAlign: "center",
                          color: "#3f8600",
                        }}
                      >
                        {day.success}
                      </td>
                      <td
                        style={{
                          padding: "12px 8px",
                          textAlign: "center",
                          color: "#cf1322",
                        }}
                      >
                        {day.failed}
                      </td>
                      <td style={{ padding: "12px 8px" }}>
                        <div
                          style={{
                            display: "flex",
                            height: 20,
                            borderRadius: 4,
                            overflow: "hidden",
                            background: "#f0f0f0",
                          }}
                        >
                          <div
                            style={{
                              width: `${successWidth}%`,
                              background: "#52c41a",
                              transition: "width 0.3s",
                            }}
                          />
                          <div
                            style={{
                              width: `${failedWidth}%`,
                              background: "#ff4d4f",
                              transition: "width 0.3s",
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

export default ReportTrendPage;
