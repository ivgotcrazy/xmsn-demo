/**
 * admin-web 路由（前端设计规范 4）：03A~03D；守卫：需登录 + admin 角色。
 */
import { createRouter, createWebHistory } from "vue-router"

import { useAuthStore } from "@/stores/auth"

const routes = [
  { path: "/", redirect: "/admin/dashboard" },
  {
    path: "/admin/login",
    name: "admin-login",
    component: () => import("@/views/admin/LoginView.vue"),
    meta: { title: "管理员登录", public: true },
  },
  {
    path: "/admin/dashboard",
    name: "admin-dashboard",
    component: () => import("@/views/admin/DashboardView.vue"),
    meta: { title: "数据概览", requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/admin/requests",
    name: "admin-requests",
    component: () => import("@/views/admin/RequestsView.vue"),
    meta: { title: "需求与匹配查看", requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/admin/vendors",
    name: "admin-vendors",
    component: () => import("@/views/admin/VendorsView.vue"),
    meta: { title: "厂商产品查看", requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/admin/customers",
    name: "admin-customers",
    component: () => import("@/views/admin/CustomersView.vue"),
    meta: { title: "客户管理", requiresAuth: true, requiresAdmin: true },
  },
  {
    path: "/admin/logs",
    name: "admin-logs",
    component: () => import("@/views/admin/LogsView.vue"),
    meta: { title: "事件日志", requiresAuth: true, requiresAdmin: true },
  },
  { path: "/:pathMatch(.*)*", redirect: "/admin/dashboard" },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${(to.meta.title as string) ?? "需脉枢纽"} · 管理后台`
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated()) {
    return { path: "/admin/login", query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && auth.role !== "admin") {
    return { path: "/admin/login", query: { redirect: to.fullPath } }
  }
  return true
})
