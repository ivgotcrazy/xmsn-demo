/**
 * B2B Service Naive UI 主题映射（面向逐步迁移）
 * ============================================================
 * 对齐 design-system/xmsn/MASTER.md。
 * 注意：naive-ui 在 JS 侧解析颜色（seemly/rgba），无法识别 CSS 变量，
 * 故此处使用 `.theme-b2b` 语义对应的**实际色值**。
 * 关键点：MASTER 把 Primary（藏青 #0F172A，品牌）与 Accent（蓝 #0369A1，交互）分开；
 * Naive 的 primaryColor 是「交互主色」，应映射到 **Accent #0369A1**，
 * 藏青 primary 用于品牌/标题，不直接作 Naive 交互色。
 * 使用：迁移后的页面在 NConfigProvider 传入此 overrides（可配合根元素 theme-b2b 类）。
 */
import type { GlobalThemeOverrides } from "naive-ui"

export const themeB2bOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#0369a1",
    primaryColorHover: "#075985",
    primaryColorPressed: "#075985",
    primaryColorSuppl: "#075985",
    successColor: "#16a34a",
    warningColor: "#d97706",
    errorColor: "#dc2626",
    textColorBase: "#020617",
    textColor1: "#0f172a",
    textColor2: "#475569",
    borderColor: "#e2e8f0",
    borderRadius: "8px",
    fontSize: "14px",
    fontFamily: '"Plus Jakarta Sans", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
}
