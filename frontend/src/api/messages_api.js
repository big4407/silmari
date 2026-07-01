import devClient from "./devClient"

export const collectMessages = async (params = {}) => {
  const { data } = await devClient.post("/messages/collect", null, { params })
  return data
}

export const fetchMessages = async (params = {}) => {
  const { data } = await devClient.get("/messages", { params })
  return data
}

export const fetchMessage = async (sn) => {
  const { data } = await devClient.get(`/messages/${sn}`)
  return data
}

export const createMessage = async (payload) => {
  const { data } = await devClient.post("/messages/manual_input", payload)
  return data
}

export const deleteMessage = async (sn) => {
  await devClient.delete(`/messages/${sn}`)
}
