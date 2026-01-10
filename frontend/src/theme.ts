/**
 * QualityFoundry 主题配置
 * 
 * 基于 Google Antigravity 风格的明亮极简主题
 */
import type { ThemeConfig } from 'antd';

export const lightTheme: ThemeConfig = {
    token: {
        // 主色调 - Google Blue
        colorPrimary: '#4285F4',
        colorInfo: '#4285F4',
        colorSuccess: '#34A853',
        colorWarning: '#FBBC04',
        colorError: '#EA4335',

        // 字体
        fontFamily: "'Google Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: 14,

        // 圆角 - 胶囊风格
        borderRadius: 8,
        borderRadiusLG: 12,
        borderRadiusSM: 6,

        // 间距
        padding: 16,
        paddingLG: 24,
        paddingSM: 12,

        // 背景色
        colorBgContainer: '#FFFFFF',
        colorBgLayout: '#F8F9FA',
        colorBgElevated: '#FFFFFF',

        // 文字颜色
        colorText: '#202124',
        colorTextSecondary: '#5F6368',
        colorTextTertiary: '#9AA0A6',

        // 边框
        colorBorder: '#DADCE0',
        colorBorderSecondary: '#E8EAED',

        // 阴影
        boxShadow: '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
        boxShadowSecondary: '0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)',
    },
    components: {
        Button: {
            borderRadius: 24, // 胶囊按钮
            borderRadiusLG: 28,
            borderRadiusSM: 20,
            controlHeight: 40,
            controlHeightLG: 48,
            controlHeightSM: 32,
        },
        Card: {
            borderRadiusLG: 16,
        },
        Menu: {
            itemBorderRadius: 8,
            itemMarginInline: 8,
        },
        Table: {
            headerBg: '#F8F9FA',
            headerColor: '#202124',
        },
        Modal: {
            borderRadiusLG: 16,
        },
        Input: {
            borderRadius: 8,
        },
        Select: {
            borderRadius: 8,
        },
    },
};

export default lightTheme;
