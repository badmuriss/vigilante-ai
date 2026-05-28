"use client";

import { useCallback, useRef, useState } from "react";
import { getConversation, sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/types";

export interface UseChat {
  messages: ChatMessage[];
  conversationId: string | null;
  isSending: boolean;
  error: string | null;
  send: (text: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  reset: () => void;
}

export function useChat(initialConversationId: string | null = null): UseChat {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(
    initialConversationId,
  );
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sendingRef = useRef(false);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sendingRef.current) return;
      sendingRef.current = true;
      setIsSending(true);
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      try {
        const res = await sendChatMessage({
          message: trimmed,
          conversation_id: conversationId ?? undefined,
        });
        setConversationId(res.conversation_id);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: res.assistant_message.content,
            citations: res.assistant_message.citations,
            tool_calls: res.assistant_message.tool_calls,
            charts: res.assistant_message.charts,
          },
        ]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao enviar mensagem");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "Não consegui responder agora. Verifique a configuração do assistente e tente de novo.",
          },
        ]);
      } finally {
        sendingRef.current = false;
        setIsSending(false);
      }
    },
    [conversationId],
  );

  const loadConversation = useCallback(async (id: string) => {
    setError(null);
    try {
      const conv = await getConversation(id);
      setConversationId(conv.id);
      setMessages(conv.messages.filter((m) => m.role !== "tool"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar conversa");
    }
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return {
    messages,
    conversationId,
    isSending,
    error,
    send,
    loadConversation,
    reset,
  };
}
