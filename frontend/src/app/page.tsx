"use client";

import Image, { type StaticImageData } from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Gauge,
  ShieldAlert,
  ShieldCheck,
  type LucideIcon,
  Video,
} from "lucide-react";

import dashboardImage from "../assets/Nano_Banana_2_Premium_3D_isometric_render_of_a_sleek__bezel_less_computer_monitor_floating_in_a_dark_4.png";
import heroImage from "../assets/Nano_Banana_2_Cinematic_wide_shot_of_a_modern_industrial_construction_site_at_dusk__volumetric_light_2.png";
import performanceImage from "../assets/Nano_Banana_2_Macro_photography_of_a_futuristic_CPU_chip_mounted_on_a_sleek_dark_circuit_board__Neon_2.png";
import ppeImage from "../assets/Nano_Banana_2_Extreme_close_up_portrait_of_a_factory_worker_s_face_and_shoulders__wearing_a_yellow_h_1.png";
import smartLogicImage from "../assets/Nano_Banana_2_A_split_screen_composition_illustrating_a_safety_monitoring_comparison__Left_side__A_w_1.png";

type ShowcaseSection = {
  eyebrow: string;
  title: string;
  description: string;
  highlights: string[];
  image: StaticImageData;
  alt: string;
  icon: LucideIcon;
  reverse?: boolean;
  gradient: string;
};

const showcaseSections: ShowcaseSection[] = [
  {
    eyebrow: "PPE Detection",
    title: "Reconhecimento de EPIs com contexto de campo",
    description:
      "A leitura visual identifica capacete, colete e outros itens obrigatorios diretamente sobre o operador, reduzindo zonas cinzentas e acelerando a resposta da equipe de seguranca.",
    highlights: [
      "Deteccao focada no colaborador em primeiro plano",
      "Apoio para configuracao dinamica por area operacional",
      "Sinalizacao imediata de ausencia de protecao obrigatoria",
    ],
    image: ppeImage,
    alt: "Operador industrial usando equipamentos de protecao individual em ambiente de fabrica.",
    icon: ShieldCheck,
    gradient: "from-stone-100 via-white to-amber-50",
  },
  {
    eyebrow: "Smart Logic",
    title: "Comparacao visual que separa conformidade de risco",
    description:
      "A camada de logica combina deteccao, regras de negocio e contexto da cena para distinguir um operador conforme de uma situacao que exige alerta imediato.",
    highlights: [
      "Leitura de multiplos objetos na mesma cena",
      "Regras orientadas por tipo de operacao",
      "Menos ruido operacional e mais prioridade real",
    ],
    image: smartLogicImage,
    alt: "Comparacao visual entre uma cena segura e outra com potencial violacao de seguranca.",
    icon: BrainCircuit,
    reverse: true,
    gradient: "from-slate-100 via-white to-stone-50",
  },
  {
    eyebrow: "Dashboard",
    title: "Visao executiva clara para acompanhar conformidade",
    description:
      "O dashboard consolida volume de violacoes, historico da sessao e indicadores de adesao para que supervisao e gestao enxerguem tendencia, risco e oportunidade de ajuste.",
    highlights: [
      "Leitura rapida de metricas criticas",
      "Historico de eventos para auditoria e analise",
      "Base visual consistente entre operacao e gestao",
    ],
    image: dashboardImage,
    alt: "Renderizacao de monitor exibindo a interface de um painel de acompanhamento.",
    icon: BarChart3,
    gradient: "from-stone-100 via-white to-slate-50",
  },
  {
    eyebrow: "Performance",
    title: "Inferencia otimizada para operar em tempo real",
    description:
      "A arquitetura foi pensada para manter resposta baixa e processamento continuo, sustentando monitoramento ao vivo sem transformar a seguranca em um gargalo operacional.",
    highlights: [
      "Pipeline pronto para baixa latencia",
      "Capacidade de sustentar analise continua",
      "Base tecnica preparada para evolucao de modelos",
    ],
    image: performanceImage,
    alt: "Chip de processamento em close representando alta performance computacional.",
    icon: Gauge,
    reverse: true,
    gradient: "from-stone-200 via-white to-slate-50",
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-16 pb-20 sm:gap-20">
      <section className="relative overflow-hidden pt-6 sm:pt-10">
        <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="relative space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/70 px-4 py-2 backdrop-blur-xl">
              <ShieldCheck className="h-4 w-4 text-[var(--accent-strong)]" />
              <span className="eyebrow !text-[10px]">Seguranca industrial de proxima geracao</span>
            </div>

            <div className="space-y-5">
              <h1 className="max-w-4xl text-5xl font-bold tracking-tight text-[var(--foreground)] sm:text-6xl lg:text-7xl">
                Vigilancia Inteligente
                <br />
                <span className="text-[var(--accent-strong)]">para sua Operacao</span>
              </h1>

              <p className="max-w-2xl text-lg leading-8 text-[var(--muted)]">
                O Vigilante.ai combina visao computacional, regras operacionais e analise em tempo real para detectar ausencia de EPIs e transformar incidentes potenciais em acao imediata.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/monitor"
                className="inline-flex items-center gap-2 rounded-full bg-[var(--accent-strong)] px-8 py-4 text-sm font-semibold text-white shadow-[0_20px_50px_-20px_rgba(30,64,175,0.6)] transition hover:-translate-y-1 hover:bg-[var(--accent)]"
              >
                Acessar Monitor
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border-strong)] bg-white/80 px-8 py-4 text-sm font-semibold text-[var(--foreground)] transition hover:-translate-y-1 hover:border-[var(--accent-strong)]"
              >
                Ver Dashboard
              </Link>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="surface-card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Cobertura</p>
                <p className="mt-3 text-2xl font-semibold">EPIs criticos</p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Capacete, colete e regras adaptaveis por operacao.</p>
              </div>
              <div className="surface-card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Resposta</p>
                <p className="mt-3 text-2xl font-semibold">Alerta imediato</p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Sinal visual para agir no exato momento da violacao.</p>
              </div>
              <div className="surface-card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">Leitura</p>
                <p className="mt-3 text-2xl font-semibold">Visao consolidada</p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Monitor e dashboard conectados na mesma narrativa operacional.</p>
              </div>
            </div>
          </div>

          <div className="surface-card relative overflow-hidden p-3 sm:p-4">
            <div className="absolute inset-0 bg-gradient-to-br from-white/40 via-transparent to-stone-200/50" />
            <div className="relative aspect-[5/4] overflow-hidden rounded-[24px] border border-white/60">
              <Image
                src={heroImage}
                alt="Vista ampla de um canteiro industrial moderno ao entardecer."
                fill
                priority
                className="object-cover"
                sizes="(min-width: 1024px) 42vw, 100vw"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div className="surface-card p-8 space-y-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50">
            <Video className="h-6 w-6 text-blue-600" />
          </div>
          <h3 className="text-xl font-bold">Monitoramento RT</h3>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            Processamento de feed em tempo real para acompanhar operadores, equipamentos e contexto sem depender de observacao manual continua.
          </p>
        </div>

        <div className="surface-card p-8 space-y-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-100 bg-rose-50">
            <ShieldAlert className="h-6 w-6 text-rose-600" />
          </div>
          <h3 className="text-xl font-bold">Alertas Criticos</h3>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            Incidentes de conformidade ganham prioridade visual imediata para reduzir tempo de reacao e aumentar rastreabilidade da ocorrencia.
          </p>
        </div>

        <div className="surface-card p-8 space-y-4 sm:col-span-2 lg:col-span-1">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50">
            <BarChart3 className="h-6 w-6 text-slate-700" />
          </div>
          <h3 className="text-xl font-bold">Analise de Dados</h3>
          <p className="text-sm leading-relaxed text-[var(--muted)]">
            Historico, consolidacao e leitura executiva para orientar ajustes operacionais com mais base e menos intuicao.
          </p>
        </div>
      </section>

      {showcaseSections.map(({ eyebrow, title, description, highlights, image, alt, icon: Icon, reverse, gradient }) => (
        <section key={eyebrow} className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
          <div className={reverse ? "order-1 lg:order-2" : "order-1"}>
            <div className="surface-card p-8 sm:p-10">
              <div className="inline-flex items-center gap-3 rounded-full border border-[var(--border)] bg-white/80 px-4 py-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-blue-700">
                  <Icon className="h-4 w-4" />
                </span>
                <span className="eyebrow !text-[10px]">{eyebrow}</span>
              </div>

              <h2 className="mt-6 max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
              <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)] sm:text-lg">{description}</p>

              <div className="mt-6 grid gap-3">
                {highlights.map((highlight) => (
                  <div key={highlight} className="flex items-start gap-3 rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3">
                    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent-strong)]" />
                    <p className="text-sm leading-6 text-[var(--muted-strong)]">{highlight}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className={reverse ? "order-2 lg:order-1" : "order-2"}>
            <div className="surface-card relative overflow-hidden p-3 sm:p-4">
              <div className={`absolute inset-0 bg-gradient-to-br ${gradient}`} />
              <div className="relative aspect-[16/10] overflow-hidden rounded-[24px] border border-white/60">
                <Image
                  src={image}
                  alt={alt}
                  fill
                  className="object-cover"
                  sizes="(min-width: 1024px) 42vw, 100vw"
                />
              </div>
            </div>
          </div>
        </section>
      ))}

      <section className="surface-card relative overflow-hidden p-8 sm:p-10 lg:p-12">
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-4">
            <p className="eyebrow">Equipe</p>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Conheca quem construiu o Vigilante.ai</h2>
            <p className="text-base leading-7 text-[var(--muted)] sm:text-lg">
              A equipe do projeto agora tem uma pagina dedicada, com os integrantes responsaveis pela concepcao, produto e execucao tecnica da plataforma.
            </p>
          </div>

          <Link
            href="/equipe"
            className="inline-flex w-fit items-center gap-2 rounded-full bg-[var(--accent-strong)] px-6 py-3 text-sm font-semibold text-white shadow-[0_20px_50px_-20px_rgba(30,64,175,0.6)] transition hover:-translate-y-1 hover:bg-[var(--accent)]"
          >
            Ver equipe completa
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
