import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function AppShell({ title, subtitle, actions, children }: AppShellProps) {
  return (
    <div className="flex h-dvh overflow-hidden bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-border bg-bg-elevated px-4 md:gap-6 md:px-8">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold tracking-tight text-text">{title}</h1>
            {subtitle && (
              <p className="hidden truncate text-xs text-text-muted sm:block">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-4 pb-24 md:p-8">{children}</main>
      </div>
    </div>
  );
}
