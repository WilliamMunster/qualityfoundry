/**
 * QualityFoundry 主题配置
 * 
 * 高端 AI 工作台风格：深靛蓝基底 + 翡翠绿点缀
 */
import type { ThemeConfig } from 'antd';

export const lightTheme: ThemeConfig = {
    token: {
        // 主色调 - Deep Indigo
        colorPrimary: '#6366F1',
        colorInfo: '#6366F1',
        colorSuccess: '#10B981', // Emerald Green
        colorWarning: '#F59E0B',
        colorError: '#EF4444',

        // 字体 - 更现代的 Inter / Google Sans
        fontFamily: "'Inter', 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: 14,

        // 圆角 - 显著的大圆角 (Stage 2 要求 16px+)
        borderRadius: 12,
        borderRadiusLG: 16,
        borderRadiusSM: 8,

        // 间距
        padding: 16,
        paddingLG: 24,
        paddingSM: 12,

        // 背景色
        colorBgContainer: '#FFFFFF',
        colorBgLayout: '#F1F5F9', // 浅灰色底座
        colorBgElevated: '#FFFFFF',

        // 文字颜色
        colorText: '#1E293B',
        colorTextSecondary: '#475569',
        colorTextTertiary: '#94A3B8',

        // 边框
        colorBorder: '#E2E8F0',
        colorBorderSecondary: '#F1F5F9',

        // 阴影 - 更轻、更有深度的阴影
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        boxShadowSecondary: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    },
    components: {
        Button: {
            borderRadius: 12,
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 32,
            fontWeight: 600,
        },
        Card: {
            borderRadiusLG: 20,
            boxShadowTertiary: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        },
        Menu: {
            itemBorderRadius: 10,
            itemMarginInline: 12,
            itemSelectedBg: '#EEF2FF',
            itemSelectedColor: '#6366F1',
        },
        Table: {
            headerBg: '#F8FAFC',
            headerColor: '#475569',
            headerBorderRadius: 12,
        },
        Modal: {
            borderRadiusLG: 24,
        },
        Input: {
            borderRadius: 10,
            controlHeight: 40,
        },
        Select: {
            borderRadius: 10,
            controlHeight: 40,
        },
        Tabs: {
            itemHoverColor: '#6366F1',
            itemSelectedColor: '#6366F1',
            inkBarColor: '#6366F1',
            titleFontSize: 14,
        }
    },
};

export default lightTheme;
