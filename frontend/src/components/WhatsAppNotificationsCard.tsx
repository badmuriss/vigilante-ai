"use client";

import { useEffect, useState } from "react";
import { MessageCircle, Plus, Send, Trash2 } from "lucide-react";

import {
  getWhatsAppConfig,
  testWhatsApp,
  updateWhatsAppConfig,
} from "@/lib/api";
import type { WhatsAppConfig } from "@/types";

const E164_REGEX = /^\+[1-9]\d{6,14}$/;

const TOKEN_SENTINEL_UNCHANGED = null;
const TOKEN_SENTINEL_CLEAR = "";

interface FormState {
  enabled: boolean;
  phoneNumberId: string;
  templateName: string;
  templateLanguage: string;
  includeImage: boolean;
  recipients: string[];
  // token state is special — see TOKEN_SENTINEL_* above.
  accessToken: string | null;
  // Tracks whether the user changed the password-style field, so we know
  // whether to send `null` (keep existing) or the typed value.
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
    <section className="card p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Integrações</p>
          <h2 className="mt-1 flex items-center gap-2 text-base font-semibold text-text">
            <MessageCircle size={16} strokeWidth={1.8} />
            Notificações via WhatsApp
          </h2>
          <p className="mt-1 text-xs text-text-muted">
            Quando um alerta é confirmado pela equipe, ele é enviado em segundo plano
            para os números configurados via Meta WhatsApp Cloud API.
          </p>
        </div>
        <label className="flex shrink-0 items-center gap-2 text-xs text-text-muted">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Habilitado
        </label>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label">Phone Number ID</label>
          <input
            className="input mt-1"
            value={form.phoneNumberId}
            placeholder="123456789012345"
            onChange={(e) => setForm({ ...form, phoneNumberId: e.target.value })}
          />
        </div>

        <div>
          <label className="label">
            Access Token {hasToken && !form.accessTokenDirty && "(armazenado)"}
          </label>
          <input
            className="input mt-1"
            type="password"
            value={form.accessToken ?? ""}
            placeholder={hasToken ? "•••••••• (clique para substituir)" : "Cole o token Meta aqui"}
            onChange={(e) =>
              setForm({
                ...form,
                accessToken: e.target.value,
                accessTokenDirty: true,
              })
            }
          />
          {hasToken && form.accessTokenDirty && form.accessToken === "" && (
            <p className="mt-1 text-xs text-text-muted">
              Token será removido ao salvar.
            </p>
          )}
        </div>

        <div>
          <label className="label">Nome do template aprovado</label>
          <input
            className="input mt-1"
            value={form.templateName}
            placeholder="safety_alert_pt"
            onChange={(e) => setForm({ ...form, templateName: e.target.value })}
          />
        </div>

        <div>
          <label className="label">Idioma do template</label>
          <input
            className="input mt-1"
            value={form.templateLanguage}
            placeholder="pt_BR"
            onChange={(e) => setForm({ ...form, templateLanguage: e.target.value })}
          />
        </div>
      </div>

      <label className="mt-4 flex items-center gap-2 text-xs text-text-muted">
        <input
          type="checkbox"
          checked={form.includeImage}
          onChange={(e) => setForm({ ...form, includeImage: e.target.checked })}
        />
        Anexar foto do frame do alerta (header do template precisa ser do tipo imagem)
      </label>

      <div className="mt-6">
        <p className="label mb-2">Destinatários (E.164)</p>
        <div className="flex gap-2">
          <input
            className="input"
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
            className="btn-secondary"
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
                className="flex items-center justify-between rounded-[var(--radius-sm)] border bg-bg-sunken px-3 py-2 text-sm"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="mono-num">{num}</span>
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
          <p className="mt-2 text-xs text-text-muted">Nenhum destinatário cadastrado.</p>
        )}
      </div>

      <div className="mt-6 rounded-[var(--radius-sm)] border bg-bg-sunken p-4" style={{ borderColor: "var(--border)" }}>
        <p className="text-xs font-semibold text-text">Antes de habilitar</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-text-muted">
          <li>Crie um app no <span className="mono-num">developers.facebook.com</span> com produto WhatsApp.</li>
          <li>Obtenha um <strong>token permanente</strong> via System User do Meta Business.</li>
          <li>Aprove um template do tipo <em>Utility</em> com 3 variáveis no corpo (câmera, EPI, data/hora) e header opcional <em>image</em>.</li>
          <li>O servidor precisa de <span className="mono-num">VIGILANTE_NOTIFY_ENCRYPTION_KEY</span> definido para armazenar o token criptografado.</li>
        </ul>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="btn-primary"
          onClick={onSave}
          disabled={saving}
        >
          {saving ? "Salvando…" : "Salvar configuração"}
        </button>

        <div className="flex flex-1 items-center gap-2 sm:min-w-[280px]">
          <input
            className="input"
            value={testRecipient}
            placeholder="+5511999999999"
            onChange={(e) => setTestRecipient(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={onTest}
            disabled={testing || !testRecipient.trim()}
          >
            <Send size={14} strokeWidth={1.8} />
            {testing ? "Enviando…" : "Enviar teste"}
          </button>
        </div>
      </div>

      {feedback && (
        <p
          className={`mt-4 text-sm ${
            feedback.kind === "ok" ? "text-success" : "text-danger"
          }`}
        >
          {feedback.text}
        </p>
      )}
    </section>
  );
}
