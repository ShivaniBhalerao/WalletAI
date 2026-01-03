interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

/**
 * Message component displays a single chat message bubble
 * User messages appear on the right with a gradient background
 * Assistant messages appear on the left with a card style
 */
export function Message({ role, content, timestamp }: MessageProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`
          max-w-xs md:max-w-md lg:max-w-lg xl:max-w-2xl
          px-4 py-3 rounded-lg text-sm md:text-base
          ${
            isUser
              ? 'bg-gradient-to-r from-primary to-primary/90 text-primary-foreground rounded-br-none shadow-md'
              : 'bg-card text-card-foreground border border-border rounded-bl-none shadow-sm'
          }
        `}
      >
        {/* Content */}
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {content}
        </p>

        {/* Optional timestamp */}
        {timestamp && (
          <p
            className={`text-xs mt-1 ${
              isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
            }`}
          >
            {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
