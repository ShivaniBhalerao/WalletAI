import { createFileRoute } from "@tanstack/react-router"

import { ChatContainer } from "@/components/Chat/ChatContainer"

export const Route = createFileRoute("/_layout/chat")({
  component: ChatPage,
  head: () => ({
    meta: [
      {
        title: "Chat - Financial Assistant",
      },
    ],
  }),
})

/**
 * Chat page component - renders the financial chat interface
 * Protected by _layout authentication
 */
function ChatPage() {
  return <ChatContainer />
}
