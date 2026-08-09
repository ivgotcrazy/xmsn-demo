/**
 * Naive UI 主题映射（前端设计规范 2.3）：将设计 Token 映射进 Naive 主题。
 * 注意：naive-ui 在 JS 侧解析颜色（seemly/rgba），无法识别 CSS 变量，
 * 故此处使用与 tokens.css Primitive 一致的**实际色值**（语义与 Token 对应）。
 */
import type { GlobalThemeOverrides } from "naive-ui"

export const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#2563eb",
    primaryColorHover: "#3b82f6",
    primaryColorPressed: "#1d4ed8",
    primaryColorSuppl: "#3b82f6",
    successColor: "#16a34a",
    warningColor: "#d97706",
    errorColor: "#dc2626",
    textColorBase: "#111827",
    textColor1: "#111827",
    textColor2: "#6b7280",
    borderColor: "#e5e7eb",
    borderRadius: "8px",
    fontSize: "14px",
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
}
