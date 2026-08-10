/**
 * user-web 路由（前端设计规范 4 / 产品原型设计）：嵌套布局承载。
 * - 公共：/login /register /vendor/register（无布局，居中卡片）
 * - 厂商：/vendor/* 经 VendorLayout（左侧 240px 侧边导航 COMP-005）
 * - 买家：/buyer/* 经 MainLayout（顶部导航）
 * 守卫：requiresAuth 需登录。
 */
import { createRouter, createWebHistory } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const routes = [
  { path: "/", redirect: "/buyer/chat" },
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
    path: "/buyer/register",
    name: "buyer-register",
    component: () => import("@/views/public/BuyerRegisterView.vue"),
    meta: { title: "采购方注册", public: true },
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
    path: "/buyer",
    component: () => import("@/components/layout/MainLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "chat",
        name: "buyer-chat",
        component: () => import("@/views/buyer/ChatView.vue"),
        meta: { title: "需求对话" },
      },
      {
        path: "matches/:requestId",
        name: "buyer-match-result",
        component: () => import("@/views/buyer/MatchesResultView.vue"),
        meta: { title: "匹配结果" },
      },
      {
        path: "vendor/:vendorId",
        name: "buyer-vendor-capability",
        component: () => import("@/views/buyer/VendorCapabilityView.vue"),
        meta: { title: "厂商能力" },
      },
    ],
  },
  { path: "/:pathMatch(.*)*", redirect: "/buyer/chat" },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${(to.meta.title as string) ?? "需脉枢纽"} · 需脉枢纽`
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated()) {
    return { path: "/login", query: { redirect: to.fullPath } }
  }
  return true
})
