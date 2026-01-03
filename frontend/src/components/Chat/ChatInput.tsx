import { Send } from "lucide-react"
import { type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface ChatInputProps {
  input: string;
  isLoading: boolean;
  onInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

/**
 * ChatInput component handles user message input and submission
 * Includes character counter and disabled state during loading
 */
export function ChatInput({
  input,
  isLoading,
  onInputChange,
  onSubmit,
}: ChatInputProps) {
  const maxLength = 500;
  const isDisabled = isLoading || !input.trim();

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <div className="flex gap-3">
        <Input
          type="text"
          value={input}
          onChange={onInputChange}
          disabled={isLoading}
          placeholder="Ask me about your finances..."
          maxLength={maxLength}
          className="flex-1 text-base"
          aria-label="Chat message input"
        />
        <Button
          type="submit"
          disabled={isDisabled}
          size="default"
          className="px-6"
          aria-label="Send message"
        >
          {isLoading ? (
            <span className="text-sm">Thinking...</span>
          ) : (
            <>
              <Send className="h-4 w-4 mr-2" />
              Send
            </>
          )}
        </Button>
      </div>

      {/* Character counter */}
      <p className="text-xs text-muted-foreground px-1">
        {input.length} / {maxLength} characters
      </p>
    </form>
  );
}
