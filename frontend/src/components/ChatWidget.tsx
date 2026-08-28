"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { MessageCircle, X } from "lucide-react";
import { ChatPanel } from "@/components/ChatPanel";
import { getAccessToken } from "@/lib/api";
import { useChat } from "@/lib/useChat";

// Routes where the floating assistant should NOT appear (marketing/login and
// the full-page assistant itself).
const HIDDEN_PREFIXES = ["/login", "/assistente"];
const OPEN_KEY = "vigilante.chat_widget_open";

export function ChatWidget() {
  const pathname = usePathname();
  const chat = useChat();
  const [authed, setAuthed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(getAccessToken()));
  }, [pathname]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setOpen(window.localStorage.getItem(OPEN_KEY) === "1");
    }
  }, []);

  function toggle() {
    setOpen((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(OPEN_KEY, next ? "1" : "0");
      }
      return next;
    });
  }

  const hidden =
    pathname === "/" || HIDDEN_PREFIXES.some((p) => pathname.startsWith(p));
  if (!authed || hidden) return null;

  return (
    <>
      {open && (
        <div className="fixed bottom-20 right-4 z-50 flex h-[min(540px,calc(100dvh-6rem))] w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl border border-border bg-bg shadow-2xl md:bottom-6 md:right-24 md:max-h-[calc(100vh-3rem)] md:w-[min(380px,calc(100vw-7.5rem))]">
          <div className="flex shrink-0 items-center justify-between border-b border-border bg-bg-elevated px-4 py-3">
            <span className="flex items-center gap-2 text-sm font-semibold text-text">
              <MessageCircle size={16} className="text-[#f5a623]" />
              Assistente Vigilante.AI
            </span>
            <button
              type="button"
              onClick={toggle}
              aria-label="Fechar"
              className="grid h-7 w-7 place-items-center rounded-md text-text-muted transition hover:bg-bg hover:text-text"
            >
              <X size={16} />
            </button>
          </div>
          <div className="min-h-0 flex-1">
            <ChatPanel
              messages={chat.messages}
              isSending={chat.isSending}
              error={chat.error}
              onSend={chat.send}
              compact
            />
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={toggle}
        aria-label={open ? "Fechar assistente" : "Abrir assistente"}
        className="fixed bottom-20 right-4 z-50 grid h-12 w-12 place-items-center rounded-full bg-[#f5a623] text-white shadow-lg transition hover:brightness-105 md:bottom-6 md:right-6 md:h-14 md:w-14"
      >
        {open ? <X size={22} /> : <MessageCircle size={24} />}
      </button>
    </>
  );
}
