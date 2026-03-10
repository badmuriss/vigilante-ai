import type { Metadata } from "next";
import localFont from "next/font/local";
import Image from "next/image";
import Link from "next/link";
import "./globals.css";

const fiapLogoUrl = "https://upload.wikimedia.org/wikipedia/commons/d/d4/Fiap-logo-novo.jpg";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Vigilante.AI",
  description: "Monitoramento de seguranca do trabalho com visao computacional",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen antialiased`}>
        <div className="min-h-screen bg-[linear-gradient(180deg,#f7f4ee_0%,#eef3f1_48%,#f6f7f4_100%)] text-[var(--foreground)]">
          <header className="border-b border-[var(--border)] bg-white/70 backdrop-blur-xl">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <div>
                <p className="eyebrow">Vigilante.AI</p>
                <h1 className="mt-1 text-xl font-semibold tracking-tight">Monitoramento inteligente de segurança</h1>
              </div>
              <nav className="flex w-fit items-center gap-2 rounded-full border border-[var(--border)] bg-white/[0.85] p-1 text-sm font-medium shadow-[0_18px_40px_-32px_rgba(15,23,42,0.75)]">
                <Link
                  href="/"
                  className="rounded-full px-4 py-2 text-[var(--muted-strong)] transition hover:bg-[var(--panel)] hover:text-[var(--foreground)]"
                >
                  Início
                </Link>
                <Link
                  href="/monitor"
                  className="rounded-full px-4 py-2 text-[var(--muted-strong)] transition hover:bg-[var(--panel)] hover:text-[var(--foreground)]"
                >
                  Monitor
                </Link>
                <Link
                  href="/dashboard"
                  className="rounded-full px-4 py-2 text-[var(--muted-strong)] transition hover:bg-[var(--panel)] hover:text-[var(--foreground)]"
                >
                  Dashboard
                </Link>
                <Link
                  href="/equipe"
                  className="rounded-full px-4 py-2 text-[var(--muted-strong)] transition hover:bg-[var(--panel)] hover:text-[var(--foreground)]"
                >
                  Equipe
                </Link>
              </nav>
            </div>
          </header>

          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>

          <footer className="border-t border-[var(--border)] bg-[linear-gradient(180deg,rgba(255,255,255,0.28),rgba(23,33,38,0.04))]">
            <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.2fr_0.8fr_0.8fr]">
              <div className="space-y-3">
                <p className="eyebrow">Vigilante.AI</p>
                <h2 className="text-lg font-semibold tracking-tight">Monitoramento inteligente para ambientes de risco.</h2>
                <p className="max-w-xl text-sm leading-6 text-[var(--muted)]">
                  Projeto academico com foco em deteccao de EPIs, leitura operacional em tempo real e consolidacao visual para tomada de decisao.
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Navegacao</p>
                <div className="mt-4 flex flex-col gap-3 text-sm text-[var(--muted-strong)]">
                  <Link href="/" className="transition hover:text-[var(--foreground)]">Inicio</Link>
                  <Link href="/monitor" className="transition hover:text-[var(--foreground)]">Monitor</Link>
                  <Link href="/dashboard" className="transition hover:text-[var(--foreground)]">Dashboard</Link>
                  <Link href="/equipe" className="transition hover:text-[var(--foreground)]">Equipe</Link>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Contexto</p>
                <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted)]">
                  <div className="inline-flex overflow-hidden rounded-2xl border border-[var(--border)] bg-white px-4 py-3 shadow-sm">
                    <Image
                      src={fiapLogoUrl}
                      alt="Logo da FIAP"
                      width={110}
                      height={36}
                      className="h-7 w-auto object-contain"
                    />
                  </div>
                  <p>Visao computacional aplicada a seguranca do trabalho</p>
                  <p>2026</p>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
