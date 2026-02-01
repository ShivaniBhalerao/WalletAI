import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { MessageCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatInput } from './ChatInput';
import { LoadingIndicator } from './LoadingIndicator';
import { Message } from './Message';

/**
 * Suggested prompts for the chat interface
 * These prompts help users understand what they can ask the financial assistant
 */
const SUGGESTED_PROMPTS = [
  {
    emoji: '🛒',
    text: 'How much did I spend on groceries last month?',
    description: 'View spending by category'
  },
  {
    emoji: '☕',
    text: 'Show me all my Starbucks purchases',
    description: 'See transactions by merchant'
  },
  {
    emoji: '💳',
    text: 'What did I spend from my credit card this week?',
    description: 'Check account-specific spending'
  },
  {
    emoji: '📅',
    text: 'Show me transactions from last week',
    description: 'View transactions by date'
  }
];

/**
 * ChatContainer is the main chat interface component
 * Uses Vercel AI SDK's useChat hook for streaming responses
 * Integrates with existing authentication (access_token from localStorage)
 */
export function ChatContainer() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState('');
  
  // Get API URL from environment variables
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const chatEndpoint = `${apiUrl}/api/v1/chat`;

  // Get access token from localStorage
  const accessToken = localStorage.getItem('access_token');

  // Initialize useChat hook with backend endpoint
  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: chatEndpoint,
      headers: {
        Authorization: accessToken ? `Bearer ${accessToken}` : '',
        'Content-Type': 'application/json',
      },
    }),
    onError: (error) => {
      console.error('Chat error:', error);
    },
    onFinish: (message) => {
      console.log('Chat finished:', message);
    },
  });

  // Debug logging
  useEffect(() => {
    console.log('Chat status:', status);
    console.log('Messages:', messages);
    console.log('Error:', error);
  }, [status, messages, error]);

  const isLoading = status === 'submitted' || status === 'streaming';

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    sendMessage({ text: input });
    setInput('');
  };

  /**
   * Handle clicking on a suggested prompt
   * Populates the input field with the prompt text
   */
  const handlePromptClick = (promptText: string) => {
    if (isLoading) return;
    setInput(promptText);
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-lg">
            <MessageCircle className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-foreground">
              Financial Assistant
            </h1>
            <p className="text-sm md:text-base text-muted-foreground mt-1">
              Ask about your spending, trends, and financial insights
            </p>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <Card className="flex-1 mb-4 overflow-hidden">
        <CardContent className="p-0 h-full">
          <ScrollArea className="h-full p-4 md:p-6">
            {/* Empty State */}
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center max-w-md">
                  <div className="text-5xl mb-4">💼</div>
                  <h2 className="text-xl md:text-2xl font-semibold text-foreground mb-2">
                    Start your financial conversation
                  </h2>
                  <p className="text-muted-foreground mb-4">
                    Try asking:
                  </p>
                  <div className="space-y-2 text-left">
                    {SUGGESTED_PROMPTS.map((prompt, index) => (
                      <Card 
                        key={index}
                        className="p-3 hover:bg-accent/50 transition-colors cursor-pointer"
                        onClick={() => handlePromptClick(prompt.text)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handlePromptClick(prompt.text);
                          }
                        }}
                      >
                        <p className="text-sm text-foreground">
                          {prompt.emoji} {prompt.text}
                        </p>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="space-y-4">
              {messages.map((msg) => {
                // Extract text content from message parts
                const textContent = msg.parts
                  ?.filter((part) => part.type === 'text')
                  .map((part: any) => part.text)
                  .join('') || '';
                
                return (
                  <Message
                    key={msg.id}
                    role={msg.role as 'user' | 'assistant'}
                    content={textContent}
                  />
                );
              })}

              {/* Loading Indicator */}
              {isLoading && (
                <div className="flex justify-start">
                  <Card className="px-4 py-3 bg-card border-border">
                    <LoadingIndicator />
                  </Card>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="flex justify-center">
                  <Card className="px-4 py-3 bg-destructive/10 border-destructive/30">
                    <p className="text-sm text-destructive">
                      ⚠️ {error.message || 'An error occurred. Please try again.'}
                    </p>
                  </Card>
                </div>
              )}

              {/* Auto-scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Input Form */}
      <Card>
        <CardContent className="p-4 md:p-6">
          <ChatInput
            input={input}
            isLoading={isLoading}
            onInputChange={handleInputChange}
            onSubmit={handleSubmit}
          />
        </CardContent>
      </Card>
    </div>
  );
}
