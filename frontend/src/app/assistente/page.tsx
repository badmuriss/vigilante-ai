"use client";

import { useEffect, useState } from "react";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ChatPanel } from "@/components/ChatPanel";
import { deleteConversation, listConversations } from "@/lib/api";
import { useChat } from "@/lib/useChat";
import type { ConversationSummary } from "@/types";

export default function AssistentePage() {
  const chat = useChat();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  async function refreshList() {
    try {
      setConversations(await listConversations());
    } catch {
      /* ignore — list is best-effort */
    }
  }

  useEffect(() => {
    refreshList();
  }, []);

  // Refresh the sidebar list after each assistant reply lands.
  useEffect(() => {
    if (!chat.isSending && chat.conversationId) refreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chat.isSending]);

  async function openConversation(id: string) {
    await chat.loadConversation(id);
  }

  async function removeConversation(id: string) {
    await deleteConversation(id);
    if (chat.conversationId === id) chat.reset();
    refreshList();
  }

  return (
    <AppShell
      title="Assistente Vigilante.AI"
      subtitle="HUB conversacional — pergunte sobre alertas, câmeras e normas de segurança"
    >
      <div className="flex h-[calc(100vh-8rem)] gap-4">
        {/* Conversation list */}
        <aside className="flex w-72 shrink-0 flex-col overflow-hidden rounded-lg border border-border bg-bg-elevated">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="text-sm font-semibold text-text">Conversas</span>
            <button
              type="button"
              onClick={chat.reset}
              aria-label="Nova conversa"
              className="grid h-7 w-7 place-items-center rounded-md text-text-muted transition hover:bg-bg hover:text-text"
            >
              <MessageSquarePlus size={16} />
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto p-2">
            {conversations.length === 0 && (
              <p className="px-2 py-4 text-center text-xs text-text-muted">
                Nenhuma conversa ainda.
              </p>
            )}
            {conversations.map((c) => (
              <div
                key={c.id}
                className="group flex items-center gap-2 rounded-md px-2 py-2 transition hover:bg-bg"
                data-active={chat.conversationId === c.id}
              >
                <button
                  type="button"
                  onClick={() => openConversation(c.id)}
                  className="min-w-0 flex-1 text-left"
                >
                  <div className="truncate text-sm text-text">
                    {c.title || "Conversa"}
                  </div>
                  <div className="truncate text-xs text-text-muted">
                    {c.last_message_preview}
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => removeConversation(c.id)}
                  aria-label="Excluir"
                  className="hidden h-7 w-7 shrink-0 place-items-center rounded text-text-muted transition hover:text-red-600 group-hover:grid"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </aside>

        {/* Thread */}
        <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg border border-border bg-bg">
          <ChatPanel
            messages={chat.messages}
            isSending={chat.isSending}
            error={chat.error}
            onSend={chat.send}
          />
        </section>
      </div>
    </AppShell>
  );
}
