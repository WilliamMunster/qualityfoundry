import { defineConfig, devices } from '@playwright/test';

/**
 * QualityFoundry E2E Test Configuration
 * 
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  
  /* 测试文件匹配模式 */
  testMatch: /.*\.spec\.ts/,
  
  /* 完全并行运行 */
  fullyParallel: false, // E2E 测试共享数据库，串行执行
  
  /* 失败时禁止并行 */
  forbidOnly: !!process.env.CI,
  
  /* CI 环境下重试 2 次 */
  retries: process.env.CI ? 2 : 0,
  
  /* 并行工作数 */
  workers: 1, // E2E 测试串行
  
  /* 报告器配置 */
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  
  /* 全局测试配置 */
  use: {
    /* 基础 URL */
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    
    /* 收集 trace */
    trace: 'on-first-retry',
    
    /* 失败时截图 */
    screenshot: 'only-on-failure',
    
    /* 失败时录制视频 */
    video: 'on-first-retry',
    
    /* 视口大小 */
    viewport: { width: 1280, height: 720 },
    
    /* 动作超时 */
    actionTimeout: 10000,
    
    /* 导航超时 */
    navigationTimeout: 15000,
    
    /* 存储状态（登录态） */
    storageState: undefined, // 每个测试独立登录
  },
  
  /* 项目配置 */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // 暂只启用 Chromium 以加速 CI
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],
  
  /* 本地开发服务器配置（本地运行时使用） */
  webServer: {
    command: 'cd ../backend && uvicorn qualityfoundry.main:app --port 8000',
    url: 'http://localhost:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
  
  /* 测试输出目录 */
  outputDir: 'test-results/',
  
  /* 全局设置 */
  globalSetup: undefined, // 可添加全局初始化
  globalTeardown: undefined, // 可添加全局清理
});
