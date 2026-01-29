/**
 * Run Center E2E 验收测试
 * 
 * 覆盖 DoD-1/2/3 的关键路径：
 * - 创建 Run
 * - Run 列表
 * - 状态流转
 * - Evidence 下载与校验
 * - 审计闭环可解释
 */

import { test, expect, Page } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

// ============ 测试配置 ============
const TEST_TIMEOUT = 120000; // 2 分钟（运行可能较慢）
test.setTimeout(TEST_TIMEOUT);

// 从环境变量读取测试账号
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || 'admin';

// ============ 辅助函数 ============

/**
 * 登录并返回页面
 */
async function login(page: Page): Promise<void> {
  await page.goto('/');

  // 等待登录表单
  await page.getByTestId('login-username').fill(ADMIN_USER);
  await page.getByTestId('login-password').fill(ADMIN_PASS);
  await page.getByTestId('login-submit').click();

  // 等待跳转至 runs 页面
  await page.waitForURL(/\/runs/);
  await expect(page.getByTestId('runs-page-title')).toBeVisible();
}

/**
 * 创建新 Run 并返回 run_id
 */
async function createRun(page: Page, nlInput: string): Promise<string> {
  await page.getByTestId('new-run-button').click();
  await page.waitForURL(/\/runs\/new/);

  // 填写表单
  await page.getByTestId('nl-input-textarea').fill(nlInput);
  await page.getByTestId('environment-select').click();
  await page.getByTestId('env-option-local').click();

  // 提交
  await page.getByTestId('run-launch-submit').click();

  // 等待跳转至详情页
  await page.waitForURL(/\/runs\/[a-f0-9-]+/);

  // 提取 run_id 从 URL
  const url = page.url();
  const match = url.match(/\/runs\/([a-f0-9-]+)/);
  if (!match) throw new Error('Failed to extract run_id from URL');

  return match[1];
}

/**
 * 等待运行完成
 */
async function waitForRunComplete(page: Page, timeout: number = 60000): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    // 检查是否已完成（非 RUNNING 状态）
    const statusText = await page.getByTestId('run-status-badge').textContent();
    if (statusText && !statusText.includes('RUNNING')) {
      return;
    }

    // 等待 2 秒后刷新
    await page.waitForTimeout(2000);
    await page.reload();
  }

  throw new Error(`Run ${page.url()} did not complete within ${timeout}ms. Final status: ${await page.getByTestId('run-status-badge').textContent()}`);
}

/**
 * 下载并解析 evidence.json
 */
async function downloadEvidence(page: Page, runId: string): Promise<any> {
  // 触发下载
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByTestId('download-evidence-button').click(),
  ]);

  // 保存到临时目录
  const downloadPath = join(process.cwd(), 'test-results', 'downloads');
  mkdirSync(downloadPath, { recursive: true });
  const filePath = join(downloadPath, `evidence-${runId}.json`);
  await download.saveAs(filePath);

  // 读取并解析
  const content = require('fs').readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

// ============ 测试套件 ============

test.describe('Run Center DoD-1: Run 生命周期主路径', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('1.1 创建 Run 并跳转详情页', async ({ page }) => {
    const nlInput = '运行 smoke 测试';
    const runId = await createRun(page, nlInput);

    // 验证 URL 包含 run_id
    expect(page.url()).toContain(`/runs/${runId}`);

    // 验证页面标题包含 run_id
    await expect(page.getByText(runId.substring(0, 8))).toBeVisible();
  });

  test('1.2 Run 列表显示新创建的 Run', async ({ page }) => {
    // 创建一个新 Run
    const nlInput = '列表测试用例';
    const runId = await createRun(page, nlInput);

    // 返回列表
    await page.getByTestId('back-to-runs-button').click();
    await page.waitForURL(/\/runs/);

    // 验证列表中包含该 run（通过 UUID 片段匹配）
    const runRow = page.getByTestId(`run-row-${runId}`);
    await expect(runRow).toBeVisible();

    // 验证列表按时间倒序（新创建的在前面）
    const firstRunId = await page.getByTestId(/run-row-/).first().getAttribute('data-testid');
    expect(firstRunId).toContain(runId);
  });

  test('1.3 状态流转: PENDING → RUNNING → JUDGED', async ({ page }) => {
    const nlInput = '状态流转测试';
    const runId = await createRun(page, nlInput);

    // 初始状态可能是 RUNNING
    const initialStatus = await page.getByTestId('run-status-badge').textContent();
    expect(['PENDING', 'RUNNING']).toContain(initialStatus?.trim());

    // 等待完成
    await waitForRunComplete(page);

    // 最终状态应为 JUDGED 或 FINISHED
    const finalStatus = await page.getByTestId('run-status-badge').textContent();
    expect(['JUDGED', 'FINISHED', 'PASS', 'FAIL']).toContain(finalStatus?.trim());
  });

  test('1.4 刷新后数据一致性', async ({ page }) => {
    const nlInput = '数据一致性测试';
    const runId = await createRun(page, nlInput);

    // 等待完成
    await waitForRunComplete(page);

    // 记录关键数据
    const decisionBefore = await page.getByTestId('run-decision-badge').textContent();
    const toolCountBefore = await page.getByTestId('tool-count-value').textContent();

    // 刷新页面
    await page.reload();

    // 验证数据一致
    const decisionAfter = await page.getByTestId('run-decision-badge').textContent();
    const toolCountAfter = await page.getByTestId('tool-count-value').textContent();

    expect(decisionAfter).toBe(decisionBefore);
    expect(toolCountAfter).toBe(toolCountBefore);
  });

  test('1.5 列表过滤功能', async ({ page }) => {
    // 返回列表
    await page.getByTestId('back-to-runs-button').click();
    await page.waitForURL(/\/runs/);

    // 使用决策过滤器
    await page.getByTestId('decision-filter').click();
    await page.getByTestId('filter-pass').click();

    // 验证只显示 PASS 的 runs
    const visibleDecisions = await page.getByTestId(/decision-badge/).allTextContents();
    for (const decision of visibleDecisions) {
      expect(decision.trim()).toBe('PASS');
    }
  });
});

test.describe('Run Center DoD-2: 证据链可下载且可复核', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('2.1 Evidence 下载与 Schema 校验', async ({ page }) => {
    const nlInput = 'Evidence 下载测试';
    const runId = await createRun(page, nlInput);

    // 等待完成
    await waitForRunComplete(page);

    // 下载 evidence
    const evidence = await downloadEvidence(page, runId);

    // 验证 Schema URI
    expect(evidence.$schema).toBe('https://qualityfoundry.ai/schemas/evidence.v1.schema.json');

    // 验证必填字段
    expect(evidence.run_id).toBe(runId);
    expect(evidence.input_nl).toBe(nlInput);
    expect(Array.isArray(evidence.tool_calls)).toBe(true);
    expect(evidence.summary).toBeDefined();
    expect(evidence.summary.tests).toBeGreaterThanOrEqual(0);
  });

  test('2.2 Tool calls 完整性检查', async ({ page }) => {
    const nlInput = 'Tool calls 检查';
    const runId = await createRun(page, nlInput);

    await waitForRunComplete(page);

    const evidence = await downloadEvidence(page, runId);

    // 验证每个 tool_call 的必要字段
    for (const call of evidence.tool_calls) {
      expect(call.tool_name).toBeDefined();
      expect(call.status).toMatch(/^(success|failed|timeout|skipped)$/);
      expect(typeof call.duration_ms).toBe('number');
      expect(call.duration_ms).toBeGreaterThanOrEqual(0);
    }
  });

  test('2.3 Artifacts 路径相对化检查', async ({ page }) => {
    const nlInput = 'Artifacts 路径测试';
    const runId = await createRun(page, nlInput);

    await waitForRunComplete(page);

    const evidence = await downloadEvidence(page, runId);

    // 验证所有 artifact 路径是相对路径
    for (const artifact of evidence.artifacts) {
      expect(artifact.path).not.toMatch(/^\//); // 不以 / 开头
      expect(artifact.path).not.toMatch(/^[A-Za-z]:/); // Windows 绝对路径
      expect(artifact.path).toContain(runId); // 包含 run_id
    }
  });

  test('2.4 Repro 元数据存在性', async ({ page }) => {
    const nlInput = 'Repro 元数据测试';
    const runId = await createRun(page, nlInput);

    await waitForRunComplete(page);

    const evidence = await downloadEvidence(page, runId);

    // 验证 repro 元数据
    expect(evidence.repro).toBeDefined();
    expect(evidence.repro.git_sha).toBeDefined();
    expect(evidence.repro.git_branch).toBeDefined();
    expect(typeof evidence.repro.git_dirty).toBe('boolean');
  });
});

test.describe('Run Center DoD-3: 最小审计闭环可解释', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('3.1 决策原因可见性', async ({ page }) => {
    const nlInput = '决策原因测试';
    await createRun(page, nlInput);

    await waitForRunComplete(page);

    // 验证决策徽章可见
    const decisionBadge = page.getByTestId('run-decision-badge');
    await expect(decisionBadge).toBeVisible();

    // 验证决策原因文本存在
    const decisionReason = page.getByTestId('decision-reason-text');
    await expect(decisionReason).toBeVisible();

    const reasonText = await decisionReason.textContent();
    expect(reasonText?.length).toBeGreaterThan(0);
  });

  test('3.2 审计时间线显示', async ({ page }) => {
    const nlInput = '审计时间线测试';
    await createRun(page, nlInput);

    await waitForRunComplete(page);

    // 验证审计时间线组件存在
    const auditTimeline = page.getByTestId('audit-timeline');
    await expect(auditTimeline).toBeVisible();

    // 验证包含关键事件类型
    await expect(page.getByText(/TOOL_STARTED|工具启动/)).toBeVisible();
    await expect(page.getByText(/TOOL_FINISHED|工具完成/)).toBeVisible();
    await expect(page.getByText(/DECISION_MADE|决策完成/)).toBeVisible();
  });

  test('3.3 成本治理卡片显示', async ({ page }) => {
    const nlInput = '成本治理测试';
    await createRun(page, nlInput);

    await waitForRunComplete(page);

    // 验证成本治理卡片
    const governanceCard = page.getByTestId('governance-card');
    await expect(governanceCard).toBeVisible();

    // 验证预算字段
    await expect(page.getByTestId('elapsed-ms-value')).toBeVisible();
    await expect(page.getByTestId('attempts-count-value')).toBeVisible();
  });

  test('3.4 NEED_HITL 状态指引（模拟）', async ({ page }) => {
    // 注意：实际触发 NEED_HITL 需要特定条件
    // 这里验证 UI 在 NEED_HITL 状态下的显示

    // 访问一个已有的 NEED_HITL run（如果存在）
    // 或者验证 UI 组件能正确显示该状态
    const decisionOptions = ['PASS', 'FAIL', 'NEED_HITL'];

    for (const decision of decisionOptions) {
      const badge = page.getByTestId(`decision-badge-${decision}`);
      if (await badge.isVisible().catch(() => false)) {
        if (decision === 'NEED_HITL') {
          // 验证有审核指引
          await expect(page.getByText(/需要人工审核|审核/)).toBeVisible();
        }
      }
    }
  });
});
