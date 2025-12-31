/**
 * LoadingIndicator shows animated bouncing dots while waiting for assistant response
 * Uses staggered animation delays for a wave effect
 */
export function LoadingIndicator() {
  return (
    <div className="flex gap-1 items-center py-1">
      <div className="w-2 h-2 bg-primary rounded-full animate-bounce" />
      <div
        className="w-2 h-2 bg-primary rounded-full animate-bounce"
        style={{ animationDelay: '0.2s' }}
      />
      <div
        className="w-2 h-2 bg-primary rounded-full animate-bounce"
        style={{ animationDelay: '0.4s' }}
      />
    </div>
  );
}
