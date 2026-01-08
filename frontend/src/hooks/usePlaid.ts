import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import axios from "axios"

import useCustomToast from "./useCustomToast"
import { handleError } from "@/utils"

/**
 * Plaid Link Token Response
 */
export interface PlaidLinkTokenResponse {
  link_token: string
  expiration: string
}

/**
 * Plaid Exchange Request
 */
export interface PlaidExchangeRequest {
  public_token: string
  institution_name: string
}

/**
 * Plaid Sync Response
 */
export interface PlaidSyncResponse {
  total_added: number
  total_modified: number
  total_removed: number
  items_synced: number
}

/**
 * Plaid Item Public
 */
export interface PlaidItemPublic {
  id: string
  user_id: string
  item_id: string
  institution_name: string
  cursor: string | null
}

/**
 * Plaid Status Response
 */
export interface PlaidStatusResponse {
  is_connected: boolean
  items: PlaidItemPublic[]
}

/**
 * Message Response
 */
export interface Message {
  message: string
}

// Get the API base URL from the OpenAPI client configuration
const getApiUrl = (path: string) => {
  const baseUrl = localStorage.getItem("api_url") || "http://localhost:8000"
  return `${baseUrl}/api/v1${path}`
}

// Create an axios instance with authorization
const createAuthorizedAxios = () => {
  const token = localStorage.getItem("access_token")
  return axios.create({
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Hook to check Plaid connection status
 * 
 * Returns the connection status and list of connected PlaidItems
 */
export const usePlaidStatus = () => {
  return useQuery<PlaidStatusResponse, Error>({
    queryKey: ["plaidStatus"],
    queryFn: async () => {
      const api = createAuthorizedAxios()
      const response = await api.get<PlaidStatusResponse>(getApiUrl("/plaid/status"))
      return response.data
    },
  })
}

/**
 * Hook to get a Plaid Link token
 * 
 * This token is used to initialize the Plaid Link component
 */
export const usePlaidLinkToken = (enabled = false) => {
  return useQuery<PlaidLinkTokenResponse, Error>({
    queryKey: ["plaidLinkToken"],
    queryFn: async () => {
      const api = createAuthorizedAxios()
      const response = await api.get<PlaidLinkTokenResponse>(getApiUrl("/plaid/link-token"))
      return response.data
    },
    enabled,
    // Link tokens expire, so don't cache them for long
    staleTime: 0,
    gcTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to exchange a public token for an access token
 * 
 * This is called after the user successfully connects their bank account
 * through Plaid Link
 */
export const usePlaidExchange = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async (data: PlaidExchangeRequest) => {
      const api = createAuthorizedAxios()
      const response = await api.post<Message>(getApiUrl("/plaid/exchange-token"), data)
      return response.data
    },
    onSuccess: (data) => {
      showSuccessToast(data.message)
      // Invalidate status query to refresh the connection status
      queryClient.invalidateQueries({ queryKey: ["plaidStatus"] })
    },
    onError: (error: any) => {
      handleError.call(showErrorToast, error)
    },
  })
}

/**
 * Hook to sync transactions from Plaid
 * 
 * This fetches the latest transactions from all connected bank accounts
 */
export const usePlaidSync = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: async () => {
      const api = createAuthorizedAxios()
      const response = await api.post<PlaidSyncResponse>(getApiUrl("/plaid/sync"))
      return response.data
    },
    onSuccess: (data) => {
      const message = `Synced ${data.total_added} new transaction(s) from ${data.items_synced} account(s)`
      showSuccessToast(message)
      // Invalidate relevant queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["plaidStatus"] })
    },
    onError: (error: any) => {
      handleError.call(showErrorToast, error)
    },
  })
}

/**
 * Main hook that provides all Plaid-related functionality
 * 
 * Usage:
 * ```tsx
 * const { status, linkToken, exchange, sync } = usePlaid()
 * ```
 */
export const usePlaid = () => {
  const status = usePlaidStatus()
  const exchange = usePlaidExchange()
  const sync = usePlaidSync()

  return {
    status,
    exchange,
    sync,
  }
}

export default usePlaid
