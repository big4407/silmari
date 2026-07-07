import devClient, { setStoredTokens, clearStoredTokens } from "./devClient"

export const login = async (username, password) => {
  const { data } = await devClient.post("/api/v1/auth/login", { username, password })
  setStoredTokens(data)
  return data
}

export const bootstrapLogin = async () => {
  const { data } = await devClient.post("/api/v1/auth/dev/bootstrap-login")
  setStoredTokens(data)
  return data
}

export const signup = async (payload) => {
  const { data } = await devClient.post("/api/v1/auth/signup", payload)
  return data
}

export const refreshToken = async (refresh_token) => {
  const { data } = await devClient.post("/api/v1/auth/refresh", { refresh_token })
  setStoredTokens(data)
  return data
}

export const logout = async () => {
  await devClient.post("/api/v1/auth/logout")
  clearStoredTokens()
}

export const fetchMe = async () => {
  const { data } = await devClient.get("/api/v1/users/me")
  return data
}

export const fetchAdminUsers = async (approval_status) => {
  const params = approval_status ? { approval_status } : {}
  const { data } = await devClient.get("/api/v1/admin/users", { params })
  return data
}

export const updateUserApproval = async (userId, payload) => {
  const { data } = await devClient.patch(`/api/v1/admin/users/${userId}/approval`, payload)
  return data
}

export const fetchCaseSearchAccess = async () => {
  const { data } = await devClient.get("/api/v1/operations/case-search")
  return data
}
