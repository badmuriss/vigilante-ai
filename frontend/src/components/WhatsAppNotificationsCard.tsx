"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Info, Plus, Send, Trash2 } from "lucide-react";

import {
  getWhatsAppConfig,
  testWhatsApp,
  updateWhatsAppConfig,
} from "@/lib/api";
import type { WhatsAppConfig } from "@/types";

const E164_REGEX = /^\+[1-9]\d{6,14}$/;
const WHATSAPP_GREEN = "#25D366";
const WHATSAPP_TINT = "#E7F8EF";

function WhatsAppGlyph({ size = 22 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      fill={WHATSAPP_GREEN}
      aria-hidden="true"
      focusable="false"
    >
      <path d="M16.003 0C7.18 0 0 7.18 0 16.003c0 2.823.738 5.587 2.139 8.014L.063 32l8.146-2.137a15.953 15.953 0 0 0 7.79 1.983h.007C24.832 31.846 32 24.667 32 15.844 32 11.567 30.336 7.55 27.31 4.524A15.872 15.872 0 0 0 16.003 0zm-.005 29.18a13.182 13.182 0 0 1-6.722-1.84l-.482-.286-4.836 1.268 1.292-4.715-.314-.5a13.182 13.182 0 1 1 24.45-6.99 13.165 13.165 0 0 1-13.388 13.063zm7.226-9.86c-.397-.198-2.346-1.158-2.71-1.29-.364-.133-.628-.198-.893.198-.265.397-1.025 1.291-1.257 1.556-.232.265-.464.298-.86.099-.397-.198-1.677-.617-3.193-1.97-1.18-1.053-1.976-2.353-2.207-2.75-.232-.397-.025-.611.173-.81.178-.176.397-.464.595-.696.198-.232.265-.397.397-.661.133-.265.067-.497-.033-.696-.099-.198-.893-2.152-1.223-2.948-.323-.774-.65-.669-.893-.681l-.762-.014c-.265 0-.696.099-1.06.497-.364.397-1.39 1.358-1.39 3.312s1.423 3.842 1.622 4.107c.198.265 2.804 4.282 6.794 6.005 2.376 1.026 3.305.91 4.107.728.488-.116 2.346-.96 2.677-1.89.331-.93.331-1.722.231-1.89-.099-.165-.364-.265-.762-.464z" />
    </svg>
  );
}

const TOKEN_SENTINEL_UNCHANGED = null;
const TOKEN_SENTINEL_CLEAR = "";

interface FormState {
  enabled: boolean;
  phoneNumberId: string;
  templateName: string;
  templateLanguage: string;
  includeImage: boolean;
  recipients: string[];
  accessToken: string | null;
  accessTokenDirty: boolean;
}

function configToForm(cfg: WhatsAppConfig): FormState {
  return {
    enabled: cfg.enabled,
    phoneNumberId: cfg.phone_number_id ?? "",
    templateName: cfg.template_name ?? "",
    templateLanguage: cfg.template_language || "pt_BR",
    includeImage: cfg.include_image,
    recipients: cfg.recipients,
    accessToken: TOKEN_SENTINEL_UNCHANGED,
    accessTokenDirty: false,
  };
}

export function WhatsAppNotificationsCard() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState<FormState | null>(null);
  const [hasToken, setHasToken] = useState(false);
  const [newRecipient, setNewRecipient] = useState("");
  const [testRecipient, setTestRecipient] = useState("");
  const [feedback, setFeedback] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    getWhatsAppConfig()
      .then((cfg) => {
        setForm(configToForm(cfg));
        setHasToken(cfg.has_token);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Erro ao carregar";
        setFeedback({ kind: "err", text: msg });
      })
      .finally(() => setLoading(false));
  }, []);

  function addRecipient() {
    if (!form) return;
    const trimmed = newRecipient.trim();
    if (!trimmed) return;
    if (!E164_REGEX.test(trimmed)) {
      setFeedback({
        kind: "err",
        text: "Número inválido. Use formato E.164 (ex: +5511999999999).",
      });
      return;
    }
    if (form.recipients.includes(trimmed)) {
      setNewRecipient("");
      return;
    }
    setForm({ ...form, recipients: [...form.recipients, trimmed] });
    setNewRecipient("");
    setFeedback(null);
  }

  function removeRecipient(num: string) {
    if (!form) return;
    setForm({ ...form, recipients: form.recipients.filter((r) => r !== num) });
  }

  async function onSave() {
    if (!form) return;
    setSaving(true);
    setFeedback(null);
    try {
      const tokenPayload = form.accessTokenDirty
        ? form.accessToken === ""
          ? TOKEN_SENTINEL_CLEAR
          : form.accessToken
        : TOKEN_SENTINEL_UNCHANGED;
      const cfg = await updateWhatsAppConfig({
        enabled: form.enabled,
        phone_number_id: form.phoneNumberId || null,
        access_token: tokenPayload,
        template_name: form.templateName || null,
        template_language: form.templateLanguage || "pt_BR",
        recipients: form.recipients,
        include_image: form.includeImage,
      });
      setForm(configToForm(cfg));
      setHasToken(cfg.has_token);
      setFeedback({ kind: "ok", text: "Configuração salva." });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao salvar";
      setFeedback({ kind: "err", text: msg });
    } finally {
      setSaving(false);
    }
  }

  async function onTest() {
    if (!testRecipient || !form) return;
    if (!E164_REGEX.test(testRecipient.trim())) {
      setFeedback({
        kind: "err",
        text: "Número de teste inválido. Use E.164 (ex: +5511999999999).",
      });
      return;
    }
    setTesting(true);
    setFeedback(null);
    try {
      const result = await testWhatsApp(testRecipient.trim());
      if (result.ok) {
        setFeedback({
          kind: "ok",
          text: `Mensagem de teste enviada${result.message_id ? ` (id: ${result.message_id})` : ""}.`,
        });
      } else {
        setFeedback({
          kind: "err",
          text: result.error || "Falha ao enviar teste.",
        });
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
        <p className="text-sm text-text-muted">Carregando notificações…</p>
      </section>
    );
  }

  if (!form) {
    return (
      <section className="card p-6">
        <p className="text-sm text-text-muted">
          {feedback?.text ?? "Não foi possível carregar a configuração."}
        </p>
      </section>
    );
  }

  return (
    <section className="card overflow-hidden">
      {/* Header */}
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
            style={{ background: WHATSAPP_TINT }}
          >
            <WhatsAppGlyph size={22} />
          </span>
          <div className="min-w-0">
            <p className="eyebrow">Integrações</p>
            <h2 className="mt-1 text-base font-semibold text-text">
              Notificações via WhatsApp
            </h2>
            <p className="mt-1 max-w-prose text-xs text-text-muted">
              Quando um alerta é confirmado pela equipe, ele é enviado em segundo
              plano para os números configurados via Meta WhatsApp Cloud API.
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
      {/* Conexão */}
      <Section title="Conexão" description="Credenciais Meta WhatsApp Cloud API.">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="min-w-0">
            <label className="label">Phone Number ID</label>
            <input
              className="input mt-1 mono-num"
              value={form.phoneNumberId}
              placeholder="123456789012345"
              onChange={(e) => setForm({ ...form, phoneNumberId: e.target.value })}
            />
          </div>

          <div className="min-w-0">
            <div className="flex items-baseline justify-between gap-2">
              <label className="label">Access Token</label>
              {hasToken && !form.accessTokenDirty && (
                <span className="text-[10px] uppercase tracking-wider text-text-subtle">
                  armazenado
                </span>
              )}
            </div>
            <input
              className="input mt-1"
              type="password"
              value={form.accessToken ?? ""}
              placeholder={
                hasToken ? "•••••••• (clique para substituir)" : "Cole o token Meta aqui"
              }
              onChange={(e) =>
                setForm({
                  ...form,
                  accessToken: e.target.value,
                  accessTokenDirty: true,
                })
              }
            />
            {hasToken && form.accessTokenDirty && form.accessToken === "" && (
              <p className="mt-1 text-xs text-warning">
                Token será removido ao salvar.
              </p>
            )}
          </div>
        </div>
      </Section>

      {/* Template */}
      <Section
        title="Template"
        description="Template aprovado no Meta Business Manager."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="min-w-0">
            <label className="label">Nome do template</label>
            <input
              className="input mt-1"
              value={form.templateName}
              placeholder="safety_alert_pt"
              onChange={(e) => setForm({ ...form, templateName: e.target.value })}
            />
          </div>

          <div className="min-w-0">
            <label className="label">Idioma</label>
            <input
              className="input mt-1 mono-num"
              value={form.templateLanguage}
              placeholder="pt_BR"
              onChange={(e) => setForm({ ...form, templateLanguage: e.target.value })}
            />
          </div>
        </div>

        <label className="mt-4 flex items-start gap-2 text-xs text-text-muted">
          <input
            type="checkbox"
            className="mt-0.5 shrink-0"
            checked={form.includeImage}
            onChange={(e) => setForm({ ...form, includeImage: e.target.checked })}
          />
          <span>
            Anexar foto do frame do alerta. O header do template precisa ser do tipo{" "}
            <em>image</em>.
          </span>
        </label>
      </Section>

      {/* Destinatários */}
      <Section
        title="Destinatários"
        description="Números no formato E.164 (ex: +5511999999999)."
      >
        <div className="flex flex-wrap gap-2">
          <input
            className="input mono-num flex-1 sm:min-w-[220px] sm:max-w-[320px]"
            value={newRecipient}
            placeholder="+5511999999999"
            onChange={(e) => setNewRecipient(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addRecipient();
              }
            }}
          />
          <button
            type="button"
            className="btn-secondary shrink-0"
            onClick={addRecipient}
            disabled={!newRecipient.trim()}
          >
            <Plus size={14} strokeWidth={1.8} />
            Adicionar
          </button>
        </div>

        {form.recipients.length > 0 ? (
          <ul className="mt-3 space-y-1.5">
            {form.recipients.map((num) => (
              <li
                key={num}
                className="flex items-center justify-between gap-3 rounded-[var(--radius-sm)] border bg-bg-sunken px-3 py-2 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="mono-num truncate">{num}</span>
                <button
                  type="button"
                  className="btn-ghost h-7 px-2"
                  onClick={() => removeRecipient(num)}
                  aria-label={`Remover ${num}`}
                >
                  <Trash2 size={14} strokeWidth={1.8} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs text-text-subtle">
            Nenhum destinatário cadastrado.
          </p>
        )}
      </Section>

      {/* Pré-requisitos */}
      <div className="px-6 pb-6">
        <div
          className="flex gap-3 rounded-[var(--radius-md)] border bg-bg-sunken p-4"
          style={{ borderColor: "var(--border)" }}
        >
          <Info size={14} strokeWidth={1.8} className="mt-0.5 shrink-0 text-text-muted" />
          <div className="min-w-0">
            <p className="text-xs font-semibold text-text">Antes de habilitar</p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-text-muted">
              <li>
                Crie um app em{" "}
                <span className="mono-num">developers.facebook.com</span> com produto
                WhatsApp.
              </li>
              <li>
                Obtenha um <strong>token permanente</strong> via System User do Meta
                Business.
              </li>
              <li>
                Aprove um template do tipo <em>Utility</em> com 3 variáveis no corpo
                (câmera, EPI, data/hora) e header opcional <em>image</em>.
              </li>
              <li>
                O servidor precisa de{" "}
                <span className="mono-num">VIGILANTE_NOTIFY_ENCRYPTION_KEY</span>{" "}
                definido para armazenar o token criptografado.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Footer: ações */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 border-t px-6 py-4"
        style={{ borderColor: "var(--border)", background: "var(--bg-sunken)" }}
      >
        <button
          type="button"
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? "Salvando…" : "Salvar configuração"}
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <input
            className="input mono-num w-[200px]"
            value={testRecipient}
            placeholder="+5511999999999"
            onChange={(e) => setTestRecipient(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary shrink-0"
            onClick={onTest}
            disabled={testing || !testRecipient.trim()}
          >
            <Send size={14} strokeWidth={1.8} />
            {testing ? "Enviando…" : "Enviar teste"}
          </button>
        </div>
      </div>
        </>
      )}

      {feedback && (
        <p
          className={`border-t px-6 py-3 text-sm ${
            feedback.kind === "ok" ? "text-success" : "text-danger"
          }`}
          style={{ borderColor: "var(--border)" }}
        >
          {feedback.text}
        </p>
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
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="border-t px-6 py-5"
      style={{ borderColor: "var(--border)" }}
    >
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-text">{title}</h3>
        {description && (
          <p className="mt-0.5 text-xs text-text-muted">{description}</p>
        )}
      </div>
      {children}
    </div>
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
      aria-label={label}
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors"
      style={{
        background: checked ? "var(--accent)" : "var(--border-strong)",
        transitionDuration: "var(--dur-fast)",
      }}
    >
      <span
        className="inline-block h-4 w-4 rounded-full bg-white shadow-sm"
        style={{
          transform: checked ? "translateX(18px)" : "translateX(2px)",
          transition: "transform var(--dur) var(--ease)",
        }}
      />
    </button>
  );
}
