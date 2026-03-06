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
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-white text-gray-900`}
      >
        <header className="border-b border-gray-200 bg-gray-50">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <h1 className="text-xl font-bold tracking-tight">Vigilante.AI</h1>
            <nav className="flex gap-6 text-sm font-medium">
              <Link
                href="/"
                className="text-gray-600 transition-colors hover:text-gray-900"
              >
                Monitor
              </Link>
              <Link
                href="/dashboard"
                className="text-gray-600 transition-colors hover:text-gray-900"
              >
                Dashboard
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-screen-xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
