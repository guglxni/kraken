"use client";

import { useState } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

/**
 * ChatSidebar
 *
 * Client Component. Provides a natural-language query interface over KRAKEN.
 * Sends messages to the /api/chat endpoint (streaming) and renders the
 * conversation inline.
 *
 * Note: CopilotKit integration is wired here via the useCopilotChat hook once
 * the backend CopilotKit runtime endpoint is available. Until then, the sidebar
 * uses the /api/chat fetch wrapper so the UI compiles and runs today.
 */
export function ChatSidebar() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) {
        throw new Error(`Chat API error: ${res.status}`);
      }

      const data = (await res.json()) as { reply: string };

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.reply,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Unable to reach the KRAKEN API. Start the Python backend with \`kraken serve\`.`,
      };
      setMessages((prev) => [...prev, errorMsg]);
      // Log the actual error for diagnostics (not surfaced to the user)
      console.error("[ChatSidebar] fetch failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  return (
    <aside className="w-80 shrink-0 border-l border-[var(--color-border)] flex flex-col bg-[var(--color-surface-raise)]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Voyage Assistant</h2>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Ask about incidents, deployments, or sprint health.
        </p>
      </div>

      {/* Message thread */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {messages.length === 0 && (
          <p className="text-xs text-[var(--color-text-muted)] text-center mt-6">
            No messages yet. Try:{" "}
            <em>&quot;What deployments happened in the last 24 hours?&quot;</em>
          </p>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-[var(--color-teal)]/20 text-[var(--color-text-primary)]"
                  : "bg-[var(--color-border)] text-[var(--color-text-primary)]"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[var(--color-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-text-muted)]">
              Thinking…
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question…"
            rows={2}
            className="flex-1 resize-none rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-teal)] transition-colors"
          />
          <button
            type="button"
            onClick={() => void sendMessage()}
            disabled={!input.trim() || isLoading}
            className="self-end px-3 py-2 rounded-lg bg-[var(--color-teal)] text-[var(--color-surface)] text-xs font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            Send
          </button>
        </div>
        <p className="text-[10px] text-[var(--color-text-muted)] mt-1.5">
          Shift+Enter for newline · Enter to send
        </p>
      </div>
    </aside>
  );
}
