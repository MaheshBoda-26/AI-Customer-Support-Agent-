"use client";

import { useState, useEffect, useRef } from "react";
import { Send, Bot, User, AlertCircle, CheckCircle, Loader2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatResponse {
  response: string;
  conversation_id: string;
  ticket_created: boolean;
  escalated: boolean;
  ticket_id?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTicketNotice, setShowTicketNotice] = useState(false);
  const [showEscalationNotice, setShowEscalationNotice] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: currentInput,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const data: ChatResponse = await response.json();

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setConversationId(data.conversation_id);

      if (data.ticket_created) {
        setShowTicketNotice(true);
        setTimeout(() => setShowTicketNotice(false), 5000);
      }

      if (data.escalated) {
        setShowEscalationNotice(true);
      }
    } catch (err) {
      setError("Failed to send message. Please try again.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto bg-surface border border-border">
      {/* Header */}
      <header className="p-4 border-b border-border bg-surface sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-text-primary">Support Assistant</h1>
            <p className="text-xs text-text-secondary">We&apos;re here to help 24/7</p>
          </div>
        </div>
      </header>

      {/* Notices */}
      {(showTicketNotice || showEscalationNotice) && (
        <div className="px-4 py-2 border-b border-border">
          {showTicketNotice && (
            <div className="mb-2 p-2 bg-warning/10 border border-warning/30 rounded-lg text-warning text-sm flex items-center gap-2">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>A support ticket has been created for your request. Our team will follow up.</span>
            </div>
          )}
          {showEscalationNotice && (
            <div className="p-2 bg-danger/10 border border-danger/30 rounded-lg text-danger text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>You&apos;re being connected to a human agent. Please hold on.</span>
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4 space-y-4" ref={messagesEndRef}>
        {messages.length === 0 && (
          <div className="text-center text-text-secondary py-8">
            <Bot className="w-12 h-12 mx-auto text-primary/30 mb-3" />
            <p className="text-base">Hello! How can I help you today?</p>
            <p className="text-sm mt-1">Ask me anything about our products, services, or policies.</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                message.role === "user"
                  ? "bg-primary text-white"
                  : "bg-muted text-text-secondary"
              }`}
            >
              {message.role === "user" ? (
                <User className="w-4 h-4" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
            </div>
            <div
              className={`max-w-[70%] px-4 py-2 rounded-2xl ${
                message.role === "user"
                  ? "bg-primary text-white rounded-tr-sm"
                  : "bg-surface border border-border rounded-tl-sm"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className={`text-xs mt-1 ${message.role === "user" ? "text-primary/70" : "text-text-secondary"}`}>
                {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
              <Loader2 className="w-4 h-4 text-text-secondary animate-spin" />
            </div>
            <div className="px-4 py-2 bg-surface border border-border rounded-2xl rounded-tl-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-text-secondary/30 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-text-secondary/30 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-text-secondary/30 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-danger/10 border-t border-danger/30 text-danger text-sm text-center">
          {error}
        </div>
      )}

      {/* Input */}
      <form onSubmit={sendMessage} className="p-4 border-t border-border bg-surface">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            rows={1}
            maxRows={5}
            className="flex-1 px-4 py-2 bg-muted border border-border rounded-lg text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary resize-none"
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(e);
              }
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-text-secondary mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}