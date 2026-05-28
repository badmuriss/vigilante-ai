"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard } from "lucide-react";
import { getAccessToken } from "@/lib/api";

export function MarketingAuthButtons() {
  // localStorage only exists on the client; render the logged-out state until
  // mounted to avoid a hydration mismatch, then swap if a token is present.
  const [authed, setAuthed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setAuthed(Boolean(getAccessToken()));
  }, []);

  if (mounted && authed) {
    return (
      <Link href="/cameras" className="btn-primary inline-flex items-center gap-1.5 text-[15px]">
        <LayoutDashboard size={16} strokeWidth={2.2} />
        Dashboard
      </Link>
    );
  }

  return (
    <>
      <Link href="/login" className="btn-ghost text-[15px]">
        Entrar
      </Link>
      <Link href="/login?mode=register" className="btn-primary text-[15px]">
        Criar conta
      </Link>
    </>
  );
}
