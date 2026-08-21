/**
 * 认证状态（Pinia）：token / 当前用户 / 角色；JWT 存储与 @xmsn/api 共享（localStorage）。
 */
import { defineStore } from "pinia"
import { ref } from "vue"

import { authGuest, getGuestToken, getToken, setGuestToken, setToken, type UserOut } from "@xmsn/api"

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
    setGuestToken(null) // 真实登录后清除游客 token
    localStorage.setItem(ROLE_KEY, u.role)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  function logout(): void {
    token.value = null
    user.value = null
    role.value = ""
    setToken(null)
    setGuestToken(null)
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(USER_KEY)
  }

  /** 局部更新当前用户并持久化（如注册厂商后回写 vendor_id）。 */
  function updateUser(partial: Partial<UserOut>): void {
    if (!user.value) return
    user.value = { ...user.value, ...partial }
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  const isAuthenticated = (): boolean => !!getToken()

  /** 是否游客模式：存在游客会话 token（sessionStorage）。 */
  const isGuest = (): boolean => !!getGuestToken()

  /** 进入游客模式：申请游客 token（不落账号）存 sessionStorage，体验结束（关窗口）即失效。 */
  async function enterGuestMode(): Promise<void> {
    const res = await authGuest()
    setGuestToken(res.access_token)
    role.value = "guest"
  }

  return { token, user, role, setAuth, updateUser, logout, isAuthenticated, isGuest, enterGuestMode }
})
