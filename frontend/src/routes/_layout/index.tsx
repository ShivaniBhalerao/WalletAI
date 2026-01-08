import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"
import PlaidButton from "@/components/Plaid/PlaidButton"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Cloud",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">
          Welcome back, nice to see you again!!!
        </p>
      </div>
      
      <div className="flex gap-4">
        <PlaidButton />
      </div>
    </div>
  )
}
