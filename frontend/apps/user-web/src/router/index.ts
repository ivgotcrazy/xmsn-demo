/**
 * user-web 路由（前端设计规范 4 / 产品原型设计）：嵌套布局承载。
 * - 公共：/login /register /vendor/register（无布局，居中卡片）
 * - 厂商：/vendor/* 经 VendorLayout（左侧 240px 侧边导航 COMP-005）
 * - 客户：/customer/* 经 MainLayout（顶部导航）
 * 守卫：requiresAuth 需登录。
 */
import { createRouter, createWebHistory } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const routes = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/public/HomeView.vue"),
    meta: { title: "首页", public: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("@/views/public/RegisterView.vue"),
    meta: { title: "选择角色", public: true },
  },
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/public/LoginView.vue"),
    meta: { title: "登录", public: true },
  },
  {
    path: "/vendor/register",
    name: "vendor-register",
    component: () => import("@/views/public/VendorRegisterView.vue"),
    meta: { title: "厂商注册", public: true },
  },
  {
    path: "/vendor/register/company",
    name: "vendor-register-company",
    component: () => import("@/views/vendor/RegisterDetailView.vue"),
    meta: { title: "企业信息", public: true },
  },
  {
    path: "/customer/register",
    name: "customer-register",
    component: () => import("@/views/public/CustomerRegisterView.vue"),
    meta: { title: "客户注册", public: true },
  },
  {
    path: "/vendor",
    component: () => import("@/components/layout/VendorLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "dashboard",
        name: "vendor-dashboard",
        component: () => import("@/views/vendor/DashboardView.vue"),
        meta: { title: "控制台" },
      },
      {
        path: "capability",
        name: "vendor-capability",
        component: () => import("@/views/vendor/CapabilityView.vue"),
        meta: { title: "能力录入" },
      },
      {
        path: "profile",
        name: "vendor-profile",
        component: () => import("@/views/vendor/ProfileView.vue"),
        meta: { title: "能力档案" },
      },
    ],
  },
  {
    path: "/customer",
    component: () => import("@/components/layout/MainLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "chat",
        name: "customer-chat",
        component: () => import("@/views/customer/ChatView.vue"),
        meta: { title: "需求对话" },
      },
      {
        path: "matches/:requestId",
        name: "customer-match-result",
        component: () => import("@/views/customer/MatchesResultView.vue"),
        meta: { title: "匹配结果" },
      },
      {
        path: "vendor/:vendorId",
        name: "customer-vendor-capability",
        component: () => import("@/views/customer/VendorCapabilityView.vue"),
        meta: { title: "厂商能力" },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/" },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  document.title = `${(to.meta.title as string) ?? "需脉枢纽"} · 需脉枢纽`
  const auth = useAuthStore()
  // 游客禁止进入厂商后台（/vendor 下除注册外的鉴权路由）
  if (auth.isGuest() && to.meta.requiresAuth && to.path.startsWith("/vendor")) {
    return { path: "/login" }
  }
  if (to.meta.requiresAuth && !auth.isAuthenticated()) {
    // 客户侧路由：未登录自动进入游客模式（开放匿名体验，不保存会话/结果）
    if (to.path.startsWith("/customer")) {
      try {
        await auth.enterGuestMode()
        return true
      } catch {
        return { path: "/login", query: { redirect: to.fullPath } }
      }
    }
    return { path: "/login", query: { redirect: to.fullPath } }
  }
  return true
})
