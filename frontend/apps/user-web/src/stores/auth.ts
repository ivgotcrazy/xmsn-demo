/**
 * 认证状态（Pinia）：token / 当前用户 / 角色；JWT 存储与 @xmsn/api 共享（localStorage）。
 */
import { defineStore } from "pinia"
import { ref } from "vue"

import { getToken, setToken, type UserOut } from "@xmsn/api"

const ROLE_KEY = "xmsn_role"
const USER_KEY = "xmsn_user"

/** 初始化时从 localStorage 恢复用户（含 vendor_id），避免刷新/深链后 auth.user 为 null。 */
function loadUser(): UserOut | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as UserOut) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(getToken())
  const user = ref<UserOut | null>(typeof localStorage !== "undefined" ? loadUser() : null)
  const role = ref<string>(typeof localStorage !== "undefined" ? (localStorage.getItem(ROLE_KEY) ?? "") : "")

  function setAuth(t: string, u: UserOut): void {
    token.value = t
    user.value = u
    role.value = u.role
    setToken(t)
    localStorage.setItem(ROLE_KEY, u.role)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  function logout(): void {
    token.value = null
    user.value = null
    role.value = ""
    setToken(null)
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const isAuthenticated = (): boolean => !!getToken()

  return { token, user, role, setAuth, logout, isAuthenticated }
})
