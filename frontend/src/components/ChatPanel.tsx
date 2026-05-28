"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartArtifact, ChatMessage } from "@/types";

const CHART_COLORS = [
  "#f5a623",
  "#2d7ff9",
  "#34c759",
  "#ff3b30",
  "#9b51e0",
  "#00b8d9",
  "#ff9500",
];

interface ChatPanelProps {
  messages: ChatMessage[];
  isSending: boolean;
  error: string | null;
  onSend: (text: string) => void;
  emptyHint?: string;
  compact?: boolean;
}

const SUGGESTIONS = [
  "Quantos alertas tive hoje?",
  "Qual câmera flagra mais violações?",
  "O que diz a NR-6 sobre EPI?",
  "Como cadastro uma câmera RTSP?",
];

export function ChatPanel({
  messages,
  isSending,
  error,
  onSend,
  emptyHint,
  compact = false,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  function submit() {
    const text = input.trim();
    if (!text || isSending) return;
    onSend(text);
    setInput("");
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"
      >
        {messages.length === 0 && (
          <div className="mx-auto mt-6 max-w-md text-center">
            <p className="text-sm text-text-muted">
              {emptyHint ??
                "Pergunte sobre alertas, câmeras, uso da plataforma ou normas de segurança (NR-6, NR-18)."}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onSend(s)}
                  className="rounded-full border border-border bg-bg-elevated px-3 py-1.5 text-xs text-text-muted transition hover:border-border-strong hover:text-text"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} compact={compact} />
        ))}

        {isSending && (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <span className="flex gap-1">
              <Dot /> <Dot delay="150ms" /> <Dot delay="300ms" />
            </span>
            <span>Pensando…</span>
          </div>
        )}

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>
        )}
      </div>

      <div className="shrink-0 border-t border-border bg-bg-elevated p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Escreva sua pergunta…"
            className="max-h-32 min-h-[40px] flex-1 resize-none rounded-md border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-border-strong"
          />
          <button
            type="button"
            onClick={submit}
            disabled={isSending || !input.trim()}
            aria-label="Enviar"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-[#f5a623] text-white transition disabled:opacity-40"
          >
            <Send size={18} strokeWidth={2} />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message, compact }: { message: ChatMessage; compact: boolean }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-[#f5a623] text-white"
            : "bg-bg-elevated text-text border border-border"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <MarkdownContent content={message.content} />
        )}

        {!isUser && message.charts && message.charts.length > 0 && (
          <div className="mt-3 space-y-3">
            {message.charts.map((chart, i) => (
              <ChatChart key={i} chart={chart} />
            ))}
          </div>
        )}

        {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
          <details className="mt-2 text-xs text-text-muted">
            <summary className="cursor-pointer select-none">
              {message.tool_calls.length} consulta(s) ao sistema
            </summary>
            <ul className="mt-1 space-y-0.5">
              {message.tool_calls.map((t, i) => (
                <li key={i} className="font-mono">
                  {t.tool}
                </li>
              ))}
            </ul>
          </details>
        )}

        {!isUser && message.citations && message.citations.length > 0 && !compact && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {message.citations.map((c) => (
              <span
                key={c.idx}
                title={c.snippet}
                className="rounded border border-border bg-bg px-1.5 py-0.5 text-[11px] text-text-muted"
              >
                [{c.idx}] {c.doc_title}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatChart({ chart }: { chart: ChartArtifact }) {
  const data = chart.data ?? [];
  return (
    <div className="rounded-lg border border-border bg-bg-elevated p-3">
      <p className="mb-2 text-xs font-semibold text-text">{chart.title}</p>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chart.chart_type === "pie" ? (
            <PieChart margin={{ top: 24, right: 8, bottom: 8, left: 8 }}>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                cx="50%"
                cy="50%"
                outerRadius={70}
                label={(e: { name?: string; value?: number }) =>
                  `${e.name ?? ""}: ${e.value ?? 0}`
                }
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          ) : chart.chart_type === "line" ? (
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="value"
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          ) : (
            <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {data.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="break-words text-sm leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="my-2">{children}</p>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="leading-snug">{children}</li>,
          h1: ({ children }) => <h1 className="mb-2 mt-3 text-base font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-3 text-sm font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-2 text-sm font-semibold">{children}</h3>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          hr: () => <hr className="my-3 border-border" />,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="underline">
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-bg px-1 py-0.5 font-mono text-[12px]">{children}</code>
          ),
          table: ({ children }) => (
            <table className="my-2 w-full border-collapse text-xs">{children}</table>
          ),
          th: ({ children }) => <th className="border border-border px-2 py-1 text-left">{children}</th>,
          td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-text-muted"
      style={{ animationDelay: delay }}
    />
  );
}
