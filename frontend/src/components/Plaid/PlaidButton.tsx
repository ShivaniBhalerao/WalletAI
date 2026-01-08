import { useCallback, useEffect, useState } from "react"
import { usePlaidLink, type PlaidLinkOnSuccess, type PlaidLinkOptions } from "react-plaid-link"
import { RefreshCw, Link as LinkIcon } from "lucide-react"

import { LoadingButton } from "@/components/ui/loading-button"
import { usePlaidStatus, usePlaidLinkToken, usePlaidExchange, usePlaidSync } from "@/hooks/usePlaid"

/**
 * PlaidButton Component
 * 
 * A button that handles Plaid Link integration for connecting bank accounts
 * and syncing transactions.
 * 
 * Features:
 * - Shows "Connect Bank" when no Plaid connection exists
 * - Shows "Sync Transactions" when already connected
 * - Opens Plaid Link modal for new connections
 * - Handles loading/error states with appropriate feedback
 * 
 * @example
 * ```tsx
 * <PlaidButton />
 * ```
 */
export const PlaidButton = () => {
  const [isLinkReady, setIsLinkReady] = useState(false)
  const [shouldFetchToken, setShouldFetchToken] = useState(false)

  // Query Plaid connection status
  const { data: statusData, isLoading: isLoadingStatus } = usePlaidStatus()

  // Fetch link token when needed (only when user clicks to connect)
  const { data: linkTokenData, isLoading: isLoadingToken } = usePlaidLinkToken(shouldFetchToken)

  // Mutation for exchanging public token
  const exchangeMutation = usePlaidExchange()

  // Mutation for syncing transactions
  const syncMutation = usePlaidSync()

  const isConnected = statusData?.is_connected || false

  /**
   * Handle successful Plaid Link completion
   */
  const onSuccess = useCallback<PlaidLinkOnSuccess>(
    (publicToken, metadata) => {
      console.log("Plaid Link success:", metadata)
      
      // Exchange the public token for an access token
      exchangeMutation.mutate({
        public_token: publicToken,
        institution_name: metadata.institution?.name || "Unknown Institution",
      })
      
      // Reset link token fetch
      setShouldFetchToken(false)
      setIsLinkReady(false)
    },
    [exchangeMutation],
  )

  /**
   * Handle Plaid Link exit (user closed the modal)
   */
  const onExit = useCallback(() => {
    console.log("Plaid Link exited")
    // Reset link token fetch
    setShouldFetchToken(false)
    setIsLinkReady(false)
  }, [])

  // Configure Plaid Link
  const config: PlaidLinkOptions = {
    token: linkTokenData?.link_token || null,
    onSuccess,
    onExit,
  }

  const { open, ready } = usePlaidLink(config)

  // Update ready state
  useEffect(() => {
    setIsLinkReady(ready)
  }, [ready])

  // Open Plaid Link when token is ready
  useEffect(() => {
    if (isLinkReady && linkTokenData?.link_token) {
      open()
    }
  }, [isLinkReady, linkTokenData, open])

  /**
   * Handle button click for connecting bank
   */
  const handleConnectClick = () => {
    setShouldFetchToken(true)
  }

  /**
   * Handle button click for syncing transactions
   */
  const handleSyncClick = () => {
    syncMutation.mutate()
  }

  // Determine button state
  const isLoading = isLoadingStatus || isLoadingToken || exchangeMutation.isPending || syncMutation.isPending
  const buttonText = isConnected ? "Sync Transactions" : "Connect Bank"
  const ButtonIcon = isConnected ? RefreshCw : LinkIcon

  return (
    <LoadingButton
      onClick={isConnected ? handleSyncClick : handleConnectClick}
      loading={isLoading}
      disabled={isLoading}
      variant="default"
      size="default"
      className="gap-2"
    >
      {!isLoading && <ButtonIcon className="h-4 w-4" />}
      {buttonText}
    </LoadingButton>
  )
}

export default PlaidButton
