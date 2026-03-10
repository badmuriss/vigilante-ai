import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, BadgeCheck, GraduationCap, Users2 } from "lucide-react";

const fiapLogoUrl = "https://upload.wikimedia.org/wikipedia/commons/d/d4/Fiap-logo-novo.jpg";

type TeamMember = {
  name: string;
  rm: string;
};

const teamMembers: TeamMember[] = [
  { name: "Felipe Neves Cavalcanti", rm: "551619" },
  { name: "Mateus Vicente", rm: "550521" },
  { name: "Gabriel Da Silva Freitas", rm: "551195" },
  { name: "Murilo Alves de Moura", rm: "98220" },
  { name: "Roberto Felix de Araujo Guedes", rm: "99976" },
];

export default function TeamPage() {
  return (
    <div className="flex flex-col gap-10 pb-16 pt-4 sm:gap-12 sm:pt-8">
      <section className="surface-card relative overflow-hidden p-8 sm:p-10 lg:p-12">
        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-5">
            <div className="flex items-center gap-4">
              <div className="overflow-hidden rounded-2xl border border-[var(--border)] bg-white px-4 py-3 shadow-sm">
                <Image
                  src={fiapLogoUrl}
                  alt="Logo da FIAP"
                  width={120}
                  height={40}
                  className="h-8 w-auto object-contain"
                />
              </div>
              <p className="eyebrow">Equipe</p>
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Time responsavel pelo Vigilante.ai</h1>
            <p className="text-base leading-8 text-[var(--muted)] sm:text-lg">
              Alunos da FIAP, engajados e focados em desenvolver uma plataforma de monitoramento com visao computacional aplicada a seguranca operacional.
            </p>
          </div>

          <Link
            href="/"
            className="inline-flex w-fit items-center gap-2 rounded-full border border-[var(--border-strong)] bg-white/80 px-6 py-3 text-sm font-semibold text-[var(--foreground)] transition hover:-translate-y-1 hover:border-[var(--accent-strong)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar para inicio
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {teamMembers.map((member) => (
          <article key={member.rm} className="surface-card p-6 sm:p-7">
            <div className="flex items-center justify-between gap-4">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50 text-blue-700">
                <Users2 className="h-6 w-6" />
              </span>
              <span className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
                RM {member.rm}
              </span>
            </div>

            <h2 className="mt-6 text-2xl font-semibold tracking-tight">{member.name}</h2>

            <div className="mt-5 space-y-3 text-sm text-[var(--muted-strong)]">
              <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3">
                <GraduationCap className="h-4 w-4 shrink-0 text-[var(--accent-strong)]" />
                <p>Aluno FIAP</p>
              </div>
              <div className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3">
                <BadgeCheck className="h-4 w-4 shrink-0 text-[var(--accent-strong)]" />
                <p>Engajado e focado na evolucao do projeto</p>
              </div>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}