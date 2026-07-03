import { theme, type ThemeConfig } from 'antd'

/**
 * 设计 token —— 从 UI 设计图「组件规范」页取真值（Tailwind 风色板）。
 * 全局用 antd ConfigProvider 应用，页面/组件不再散落硬编码色值。
 *
 * 二次迭代：引入亮/暗双主题。
 * - `palette`：真实 hex，仅供 antd `buildTheme` 计算派生色（算法需要真值）。
 * - `brand`：组件内联样式消费的对象。**表面色（文字/边框/背景）改为 CSS 变量字符串**，
 *   随 `:root[data-theme]` 自动在亮/暗间切换——因此所有既有 `style={{ color: brand.textSecondary }}`
 *   等用法「零改动」即获得暗色适配；强调色（主/成功/警告/错误）保持 hex，两套主题通用，
 *   且可安全传入 antd 组件的 strokeColor / 图表 range 等需要真值的属性。
 */

// —— 真实 hex 调色板（供 antd 算法与需要真值的场景）——
export const palette = {
  primary: '#2563EB',
  success: '#16A34A',
  warning: '#F59E0B',
  error: '#EF4444',
  // 亮色表面（作为 CSS 变量的亮色默认值，见 index.css）
  textBase: '#111827',
  textSecondary: '#6B7280',
  border: '#E5E7EB',
  bgLayout: '#F8FAFC',
  bgContainer: '#FFFFFF',
} as const

// —— 组件内联样式消费的品牌对象 ——
export const brand = {
  // 强调色：主题无关，保持 hex（可传入 strokeColor / 图表 range）
  primary: palette.primary,
  success: palette.success,
  warning: palette.warning,
  error: palette.error,
  gradientFrom: '#2563EB',
  gradientTo: '#1D39C4',
  // 表面色：走 CSS 变量，随 data-theme 切换（亮色回退值与旧版一致 → 向后兼容）
  textBase: 'var(--app-text)',
  textSecondary: 'var(--app-text-secondary)',
  border: 'var(--app-border)',
  bgLayout: 'var(--app-bg-layout)',
  bgContainer: 'var(--app-bg-container)',
} as const

export type ThemeMode = 'light' | 'dark'

/** 按主题模式构建 antd ThemeConfig；亮色保持旧观感，暗色启用 darkAlgorithm。 */
export function buildTheme(mode: ThemeMode): ThemeConfig {
  const isDark = mode === 'dark'
  return {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: palette.primary,
      colorSuccess: palette.success,
      colorWarning: palette.warning,
      colorError: palette.error,
      borderRadius: 8,
      fontFamily:
        "'Inter','PingFang SC','Microsoft YaHei',-apple-system,BlinkMacSystemFont,sans-serif",
      fontSize: 14,
      // 统一动效时长，过渡更顺滑
      motionDurationMid: '0.22s',
      motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      // 亮色维持旧版精确表面色；暗色交给算法推导，仅覆盖布局容器
      ...(isDark
        ? { colorBgLayout: '#0D1117' }
        : { colorTextBase: palette.textBase, colorBgLayout: palette.bgLayout }),
    },
    components: {
      Card: { borderRadiusLG: 12 },
      Tag: { borderRadiusSM: 999 },
      Button: { borderRadius: 8, fontWeight: 500 },
      Layout: isDark
        ? { siderBg: '#141A24', headerBg: '#141A24', bodyBg: '#0D1117' }
        : { siderBg: palette.bgContainer, headerBg: palette.bgContainer, bodyBg: palette.bgLayout },
      Menu: {
        itemSelectedBg: isDark ? '#1D2B45' : '#EFF4FF',
        itemSelectedColor: palette.primary,
        itemHeight: 44,
      },
    },
  }
}

/** 兼容旧引用：默认（亮色）主题配置。 */
export const themeConfig: ThemeConfig = buildTheme('light')
