"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Info, Send, Trash2 } from "lucide-react";

import {
  getTeamsConfig,
  testTeams,
  updateTeamsConfig,
} from "@/lib/api";
import type { TeamsConfig } from "@/types";

const TEAMS_BLUE = "#6264A7";
const TEAMS_TINT = "#ECECFA";
const WEBHOOK_SENTINEL_UNCHANGED = null;
const WEBHOOK_SENTINEL_CLEAR = "";

function TeamsGlyph({ size = 22 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 2228.833 2073.333"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M1554.637 777.5h575.713c54.391 0 98.483 44.092 98.483 98.483v524.398c0 199.901-162.051 361.952-361.952 361.952h-1.711c-199.901.028-361.975-162-362.004-361.901V828.971c.001-28.427 23.045-51.471 51.471-51.471z"
        fill="#5059C9"
      />
      <circle cx="1943.75" cy="440.583" r="233.25" fill="#5059C9" />
      <circle cx="1218.083" cy="336.917" r="336.917" fill="#7B83EB" />
      <path
        d="M1667.323 777.5H717.01c-53.743 1.33-96.257 45.931-95 99.668v598.158c-7.505 322.524 247.657 590.16 570.167 598.007 322.51-7.847 577.671-275.483 570.167-598.007V877.168c1.256-53.737-41.257-98.338-95.001-99.668z"
        fill="#7B83EB"
      />
      <path
        d="M1244 777.5v838.145c-.258 38.435-23.549 72.964-59.09 87.629-11.316 4.787-23.478 7.254-35.765 7.26H762.473c-6.738-17.105-12.95-34.21-18.122-51.834a631.287 631.287 0 0 1-27.341-183.876V877.02c-1.255-53.65 41.19-98.198 94.84-99.52H1244z"
        opacity=".1"
      />
      <path
        d="M1192.167 777.5v889.978a92.701 92.701 0 0 1-7.257 35.765c-14.665 35.541-49.194 58.832-87.629 59.09H786.597c-8.812-17.105-17.105-34.21-24.124-51.834-7.019-17.624-12.95-34.21-18.122-51.834a631.287 631.287 0 0 1-27.341-183.876V877.02c-1.255-53.65 41.19-98.198 94.84-99.52h380.317z"
        opacity=".2"
      />
      <path
        d="M1192.167 777.5v786.312c-.395 52.223-42.617 94.445-94.84 94.84h-353.012A631.287 631.287 0 0 1 717.01 1474.6V877.168c-1.255-53.737 41.257-98.339 95-99.668h380.157z"
        opacity=".2"
      />
      <path
        d="M1140.333 777.5v786.312c-.395 52.223-42.617 94.445-94.84 94.84H744.165A631.287 631.287 0 0 1 717.01 1474.6V877.168c-1.255-53.737 41.257-98.339 95-99.668h328.323z"
        opacity=".2"
      />
      <path
        d="M1244 509.193v163.156c-8.812.518-17.105 1.037-25.917 1.037-8.812 0-17.105-.518-25.917-1.037a284.472 284.472 0 0 1-51.834-8.293c-104.963-24.857-191.679-98.469-233.25-198.045a288.02 288.02 0 0 1-16.587-51.834h258.648c52.305.198 94.661 42.554 94.857 94.859z"
        opacity=".1"
      />
      <path
        d="M1192.167 561.026v111.323a284.472 284.472 0 0 1-51.834-8.293c-104.963-24.857-191.679-98.469-233.25-198.045h190.226c52.305.198 94.661 42.555 94.858 94.86z"
        opacity=".2"
      />
      <path
        d="M1140.333 561.026v103.03c-104.963-24.857-191.679-98.469-233.25-198.045h138.392c52.305.199 94.661 42.555 94.858 94.86z"
        opacity=".2"
      />
      <linearGradient
        id="teamsGradient"
        gradientUnits="userSpaceOnUse"
        x1="198.099"
        y1="1683.0726"
        x2="942.2344"
        y2="394.2607"
        gradientTransform="matrix(1 0 0 -1 0 2075.3333)"
      >
        <stop offset="0" stopColor="#5a62c3" />
        <stop offset=".5" stopColor="#4d55bd" />
        <stop offset="1" stopColor="#3940ab" />
      </linearGradient>
      <path
        d="M95.01 466.193h950.312c52.473 0 95.01 42.538 95.01 95.01v950.312c0 52.473-42.538 95.01-95.01 95.01H95.01c-52.473 0-95.01-42.538-95.01-95.01V561.203c0-52.472 42.538-95.01 95.01-95.01z"
        fill="url(#teamsGradient)"
      />
      <path
        d="M820.211 828.193H630.241v517.297H509.211V828.193H320.123V727.844h500.088v100.349z"
        fill="#FFF"
      />
    </svg>
  );
}

interface FormState {
  enabled: boolean;
  webhookUrl: string | null;
  webhookDirty: boolean;
  channelName: string;
  notifyOnConfirmed: boolean;
}

function configToForm(cfg: TeamsConfig): FormState {
  return {
    enabled: cfg.enabled,
    webhookUrl: WEBHOOK_SENTINEL_UNCHANGED,
    webhookDirty: false,
    channelName: cfg.channel_name ?? "",
    notifyOnConfirmed: cfg.notify_on_confirmed,
  };
}

function isHttpsUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !!url.host;
  } catch {
    return false;
  }
}

export function TeamsNotificationsCard() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState<FormState | null>(null);
  const [hasWebhook, setHasWebhook] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    getTeamsConfig()
      .then((cfg) => {
        setForm(configToForm(cfg));
        setHasWebhook(cfg.has_webhook_url);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Erro ao carregar";
        setFeedback({ kind: "err", text: msg });
      })
      .finally(() => setLoading(false));
  }, []);

  async function onSave() {
    if (!form) return;
    const candidate = form.webhookUrl?.trim() ?? "";
    if (form.webhookDirty && candidate !== "" && !isHttpsUrl(candidate)) {
      setFeedback({ kind: "err", text: "URL inválida. Use uma URL HTTPS do Teams Workflows." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      const webhookPayload = form.webhookDirty
        ? candidate === ""
          ? WEBHOOK_SENTINEL_CLEAR
          : candidate
        : WEBHOOK_SENTINEL_UNCHANGED;
      const cfg = await updateTeamsConfig({
        enabled: form.enabled,
        webhook_url: webhookPayload,
        channel_name: form.channelName || null,
        notify_on_confirmed: form.notifyOnConfirmed,
      });
      setForm(configToForm(cfg));
      setHasWebhook(cfg.has_webhook_url);
      setFeedback({ kind: "ok", text: "Configuração salva." });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao salvar";
      setFeedback({ kind: "err", text: msg });
    } finally {
      setSaving(false);
    }
  }

  async function onTest() {
    if (!form) return;
    if (form.webhookDirty) {
      setFeedback({ kind: "err", text: "Salve a configuração antes de enviar o teste." });
      return;
    }
    setTesting(true);
    setFeedback(null);
    try {
      const result = await testTeams();
      if (result.ok) {
        setFeedback({
          kind: "ok",
          text: `Mensagem de teste enviada${result.status_code ? ` (HTTP ${result.status_code})` : ""}.`,
        });
      } else {
        setFeedback({ kind: "err", text: result.error || "Falha ao enviar teste." });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao enviar teste";
      setFeedback({ kind: "err", text: msg });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <section className="card p-6">
        <p className="text-sm text-text-muted">Carregando Teams…</p>
      </section>
    );
  }

  if (!form) {
    return (
      <section className="card p-6">
        <p className="text-sm text-text-muted">
          {feedback?.text ?? "Não foi possível carregar a configuração do Teams."}
        </p>
      </section>
    );
  }

  return (
    <section className="card overflow-hidden">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setExpanded((v) => !v);
          }
        }}
        aria-expanded={expanded}
        className="flex w-full cursor-pointer items-start justify-between gap-4 p-6 text-left transition-colors hover:bg-bg-sunken/60"
      >
        <div className="flex min-w-0 items-start gap-3">
          <span
            className="grid h-11 w-11 shrink-0 place-items-center rounded-[var(--radius-md)]"
            style={{ background: TEAMS_TINT, color: TEAMS_BLUE }}
          >
            <TeamsGlyph size={22} />
          </span>
          <div className="min-w-0">
            <p className="eyebrow">Integrações</p>
            <h2 className="mt-1 text-base font-semibold text-text">
              Notificações via Microsoft Teams
            </h2>
            <p className="mt-1 max-w-prose text-xs text-text-muted">
              Quando um alerta é confirmado, o Vigilante.AI envia um card para
              o canal ou chat configurado no Teams Workflows.
            </p>
          </div>
        </div>
        <div
          className="flex shrink-0 items-center gap-3"
          onClick={(e) => e.stopPropagation()}
        >
          <Switch
            checked={form.enabled}
            onChange={(v) => setForm({ ...form, enabled: v })}
            label="Habilitado"
          />
          <button
            type="button"
            aria-label={expanded ? "Recolher" : "Expandir"}
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
            className="grid h-7 w-7 place-items-center rounded-full text-text-muted hover:bg-bg-sunken"
          >
            <ChevronDown
              size={18}
              strokeWidth={1.8}
              className="transition-transform"
              style={{
                transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
                transitionDuration: "var(--dur)",
              }}
            />
          </button>
        </div>
      </div>

      {expanded && (
        <>
      <Section title="Conexão" description="URL gerada pelo Teams Workflows.">
        <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
          <div className="min-w-0">
            <div className="flex items-baseline justify-between gap-2">
              <label className="label">Webhook URL</label>
              {hasWebhook && !form.webhookDirty && (
                <span className="text-[11px] text-success">URL configurada</span>
              )}
            </div>
            <input
              className="input mt-1"
              type="password"
              value={form.webhookUrl ?? ""}
              placeholder={hasWebhook ? "Webhook salvo. Cole uma nova URL para trocar." : "https://..."}
              onChange={(e) =>
                setForm({ ...form, webhookUrl: e.target.value, webhookDirty: true })
              }
            />
          </div>

          <div className="min-w-0">
            <label className="label">Nome do canal</label>
            <input
              className="input mt-1"
              value={form.channelName}
              placeholder="Segurança"
              onChange={(e) => setForm({ ...form, channelName: e.target.value })}
            />
          </div>
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            checked={form.notifyOnConfirmed}
            onChange={(e) =>
              setForm({ ...form, notifyOnConfirmed: e.target.checked })
            }
            className="h-4 w-4 cursor-pointer accent-text"
          />
          Enviar quando um alerta for confirmado
        </label>

        {hasWebhook && (
          <button
            type="button"
            onClick={() => {
              if (!form) return;
              setForm({
                ...form,
                webhookUrl: WEBHOOK_SENTINEL_CLEAR,
                webhookDirty: true,
                enabled: false,
              });
              setHasWebhook(false);
            }}
            className="mt-3 inline-flex items-center gap-1 text-xs text-danger hover:underline"
          >
            <Trash2 size={12} strokeWidth={1.8} />
            Remover webhook salvo
          </button>
        )}
      </Section>

      <Section title="Teste" description="Envia um card simples para o Teams.">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onTest}
            disabled={testing || saving || !hasWebhook}
            className="btn-secondary text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={14} strokeWidth={1.8} />
            {testing ? "Enviando…" : "Enviar teste"}
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="btn-primary text-sm disabled:cursor-wait disabled:opacity-70"
          >
            {saving ? "Salvando…" : "Salvar configuração"}
          </button>
        </div>
        <div className="mt-3 flex items-start gap-2 text-xs text-text-muted">
          <Info size={13} strokeWidth={1.8} className="mt-0.5 shrink-0" />
          <p>
            No Teams, crie um Workflow com o gatilho de webhook recebido e copie
            a URL gerada para este campo.
          </p>
        </div>
      </Section>
        </>
      )}

      {feedback && (
        <div className="border-t border-border px-6 py-3">
          <p
            className={
              "text-sm " +
              (feedback.kind === "ok" ? "text-success" : "text-danger")
            }
          >
            {feedback.text}
          </p>
        </div>
      )}
    </section>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-border px-6 py-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text">{title}</h3>
        <p className="mt-1 text-xs text-text-muted">{description}</p>
      </div>
      {children}
    </section>
  );
}

function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors"
      style={{ backgroundColor: checked ? TEAMS_BLUE : "#d4d4d4" }}
    >
      <span className="sr-only">{label}</span>
      <span
        className="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform"
        style={{ transform: checked ? "translateX(18px)" : "translateX(2px)" }}
      />
    </button>
  );
}
