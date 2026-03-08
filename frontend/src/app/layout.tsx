import type { Metadata } from "next";
import localFont from "next/font/local";
import Link from "next/link";
import "./globals.css";

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
        <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(18,103,66,0.14),transparent_24%),radial-gradient(circle_at_top_right,rgba(210,72,72,0.08),transparent_22%),linear-gradient(180deg,#f7f4ee_0%,#eef3f1_48%,#f6f7f4_100%)] text-[var(--foreground)]">
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
                  Monitor
                </Link>
                <Link
                  href="/dashboard"
                  className="rounded-full px-4 py-2 text-[var(--muted-strong)] transition hover:bg-[var(--panel)] hover:text-[var(--foreground)]"
                >
                  Dashboard
                </Link>
              </nav>
            </div>
          </header>

          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
