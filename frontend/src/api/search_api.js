import devClient from "./devClient"

export const createSearch = async (payload) => {
  const { data } = await devClient.post("/search", payload)
  return data
}

export const fetchSearches = async (params = {}) => {
  const { data } = await devClient.get("/search", { params })
  return data
}

export const fetchSearch = async (searchId) => {
  const { data } = await devClient.get(`/search/${searchId}`)
  return data
}

export const deleteSearch = async (searchId) => {
  await devClient.delete(`/search/${searchId}`)
}
