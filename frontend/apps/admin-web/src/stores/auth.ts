/**
 * 认证状态（Pinia）：token / 当前用户 / 角色（admin）。
 */
import { defineStore } from "pinia"
import { ref } from "vue"

import { getToken, setToken, type UserOut } from "@xmsn/api"

const ROLE_KEY = "xmsn_role"

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(getToken())
  const user = ref<UserOut | null>(null)
  const role = ref<string>(typeof localStorage !== "undefined" ? (localStorage.getItem(ROLE_KEY) ?? "") : "")

  function setAuth(t: string, u: UserOut): void {
    token.value = t
    user.value = u
    role.value = u.role
    setToken(t)
    localStorage.setItem(ROLE_KEY, u.role)
  }

  function logout(): void {
    token.value = null
    user.value = null
    role.value = ""
    setToken(null)
    localStorage.removeItem(ROLE_KEY)
  }

  const isAuthenticated = (): boolean => !!getToken()
  const isAdmin = (): boolean => role.value === "admin"

  return { token, user, role, setAuth, logout, isAuthenticated, isAdmin }
})
