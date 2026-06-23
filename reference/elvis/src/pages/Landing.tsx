import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Radio, Lightbulb, Workflow, BarChart3, Shield,
  ArrowRight, ChevronRight, CheckCircle2, Sparkles,
  TrendingUp, Users, Globe, MessageSquare,
  BookOpen, ExternalLink, Brain, FileText, Quote, GraduationCap,
} from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i: number) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

const stagger = {
  visible: { transition: { staggerChildren: 0.08 } },
};

function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-sm font-bold text-primary-foreground">O</span>
          </div>
          <span className="text-base font-bold text-foreground tracking-tight">Odradek</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
          <a href="#problem" className="hover:text-foreground transition-colors">Problem</a>
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-foreground transition-colors">How It Works</a>
          <a href="#learnings" className="hover:text-foreground transition-colors">Learnings</a>
          <a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/auth">
            <Button variant="ghost" size="sm" className="text-muted-foreground">Log In</Button>
          </Link>
          <Link to="/auth">
            <Button size="sm" className="gap-1.5">
              Get Started <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}

function HeroSection() {
  return (
    <section className="relative overflow-hidden pt-36 pb-20">
      {/* Masked grid + soft glow backdrop */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--border)/0.6)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border)/0.6)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_55%_45%_at_50%_0%,black,transparent)]" />
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[460px] w-[820px] rounded-full bg-primary/10 blur-[140px]" />

      <div className="relative z-10 mx-auto max-w-4xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-7 inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur-sm"
        >
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Governed feedback-to-action automation
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-balance text-5xl sm:text-6xl font-extrabold tracking-tight text-foreground leading-[1.05]"
        >
          Close the loop.{" "}
          <span className="bg-gradient-to-r from-primary via-info to-primary bg-clip-text text-transparent">
            Automatically.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground leading-relaxed"
        >
          Odradek connects every feedback source, triages it with AI, drafts the right action for
          human approval, and pushes it to the tools you already use — then measures whether the loop
          actually closed, and remembers what worked.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3"
        >
          <Link to="/auth">
            <Button size="lg" className="h-12 px-7 text-base font-semibold gap-2 shadow-sm shadow-primary/20">
              Start Free Trial <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <a href="#how-it-works">
            <Button variant="outline" size="lg" className="h-12 px-7 text-base font-semibold gap-2">
              See How It Works <ChevronRight className="h-4 w-4" />
            </Button>
          </a>
        </motion.div>

        {/* Trust badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-x-7 gap-y-2.5 text-xs font-medium text-muted-foreground"
        >
          <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5 text-primary/70" /> EU AI Act + GDPR aware</span>
          <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-primary/70" /> Human-in-the-loop by design</span>
          <span className="flex items-center gap-1.5"><FileText className="h-3.5 w-3.5 text-primary/70" /> Evidence-backed actions</span>
          <span className="flex items-center gap-1.5"><Globe className="h-3.5 w-3.5 text-primary/70" /> Your model, your cloud</span>
        </motion.div>
      </div>

      {/* Product preview — in normal flow, no overlap */}
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 mx-auto mt-16 w-[92%] max-w-5xl px-6"
      >
        <div className="rounded-xl border border-border bg-card shadow-2xl shadow-primary/5 overflow-hidden ring-1 ring-black/5">
          <div className="flex items-center gap-1.5 border-b border-border bg-secondary/40 px-4 py-2.5">
            <div className="h-2.5 w-2.5 rounded-full bg-destructive/50" />
            <div className="h-2.5 w-2.5 rounded-full bg-warning/50" />
            <div className="h-2.5 w-2.5 rounded-full bg-success/50" />
            <span className="ml-3 text-[10px] text-muted-foreground font-mono">app.odradek.io/dashboard</span>
          </div>
          <DashboardMockup />
        </div>
      </motion.div>
    </section>
  );
}

function DashboardMockup() {
  return (
    <div className="p-4 grid grid-cols-4 gap-3 h-[280px] overflow-hidden">
      {[
        { label: "Signals (7d)", value: "1,247", change: "+12%", color: "text-primary" },
        { label: "Open Insights", value: "23", change: "4 critical", color: "text-warning" },
        { label: "Actions Taken", value: "89", change: "72% auto", color: "text-success" },
        { label: "Resolution Rate", value: "94%", change: "+3.2%", color: "text-success" },
      ].map((kpi, i) => (
        <div key={i} className="rounded-lg border border-border bg-background/50 p-3">
          <div className="text-[10px] text-muted-foreground font-medium">{kpi.label}</div>
          <div className="mt-1 text-xl font-bold font-mono text-foreground">{kpi.value}</div>
          <div className={`text-[10px] font-medium ${kpi.color}`}>{kpi.change}</div>
        </div>
      ))}
      <div className="col-span-2 rounded-lg border border-border bg-background/50 p-3">
        <div className="text-[10px] text-muted-foreground font-medium mb-2">Signal Trend</div>
        <div className="flex items-end gap-1 h-[120px]">
          {[40, 55, 38, 72, 60, 85, 90, 65, 78, 95, 82, 100].map((h, i) => (
            <div key={i} className="flex-1 rounded-sm bg-primary/20 relative">
              <div className="absolute bottom-0 w-full rounded-sm bg-primary/60" style={{ height: `${h}%` }} />
            </div>
          ))}
        </div>
      </div>
      <div className="col-span-2 rounded-lg border border-border bg-background/50 p-3">
        <div className="text-[10px] text-muted-foreground font-medium mb-2">Top Themes</div>
        {["Pricing complaints", "Onboarding friction", "Feature requests", "Support delays"].map((t, i) => (
          <div key={i} className="flex items-center gap-2 mb-1.5">
            <div className="h-1.5 rounded-full bg-primary/40" style={{ width: `${90 - i * 18}%` }} />
            <span className="text-[9px] text-muted-foreground whitespace-nowrap">{t}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProblemSection() {
  const problems = [
    {
      icon: MessageSquare,
      title: "Feedback is everywhere",
      desc: "NPS surveys, support tickets, social media, reviews, Slack messages — your customer voice is fragmented across dozens of tools.",
    },
    {
      icon: TrendingUp,
      title: "Signals get buried",
      desc: "By the time a pattern surfaces in your quarterly review, you've already lost the customers who tried to warn you.",
    },
    {
      icon: Users,
      title: "No one owns the loop",
      desc: "Product reads surveys. CX reads tickets. Marketing reads reviews. Nobody connects the dots across all three.",
    },
  ];

  return (
    <section id="problem" className="relative py-32 bg-card">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUp} custom={0} className="text-sm font-semibold text-primary uppercase tracking-widest">
            The Problem
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1} className="mt-3 text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Your customers are talking.
            <br />
            <span className="text-muted-foreground">Are you listening?</span>
          </motion.h2>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          variants={stagger}
          className="grid grid-cols-1 md:grid-cols-3 gap-8"
        >
          {problems.map((p, i) => (
            <motion.div
              key={i}
              variants={fadeUp}
              custom={i}
              className="group relative rounded-2xl border border-border bg-background p-8 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
                <p.icon className="h-6 w-6 text-destructive" />
              </div>
              <h3 className="text-lg font-bold text-foreground mb-2">{p.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      icon: Radio,
      title: "Multi-source signal ingestion",
      desc: "Bring feedback in via CSV upload, a webhook endpoint, or connectors — qualitative and quantitative signals in one normalized stream.",
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      icon: Brain,
      title: "AI triage & insight synthesis",
      desc: "Each signal is scored for sentiment, theme and urgency, then clustered into insights with cross-signal severity and the evidence behind them.",
      color: "text-warning",
      bg: "bg-warning/10",
    },
    {
      icon: Workflow,
      title: "Governed action engine",
      desc: "Build routing rules with conflict resolution, choose auto-execute or human approval per action, and keep a full audit trail of everything that fires.",
      color: "text-info",
      bg: "bg-info/10",
    },
    {
      icon: BarChart3,
      title: "Closed-loop outcome measurement",
      desc: "Every action carries an outcome contract — the metric and window are set up front, so you see operational, customer and outcome closure, not just 'ticket created'.",
      color: "text-success",
      bg: "bg-success/10",
    },
    {
      icon: GraduationCap,
      title: "Experiment learning repository",
      desc: "Capture A/B results with confidence that decays as they age, and surface the most relevant past learnings the moment you plan your next move.",
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      icon: Shield,
      title: "Responsible AI, built in",
      desc: "An EU AI Act + GDPR compliance checker, human oversight on risky actions, and your choice of model — hosted or fully self-hosted on your own infrastructure.",
      color: "text-muted-foreground",
      bg: "bg-muted",
    },
  ];

  return (
    <section id="features" className="py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUp} custom={0} className="text-sm font-semibold text-primary uppercase tracking-widest">
            Features
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1} className="mt-3 text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            The complete feedback loop
          </motion.h2>
          <motion.p variants={fadeUp} custom={2} className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            From raw signal to measured outcome — every step automated, every insight actionable.
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          variants={stagger}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((f, i) => (
            <motion.div
              key={i}
              variants={fadeUp}
              custom={i}
              className="group rounded-2xl border border-border bg-card p-7 hover:border-primary/20 hover:shadow-lg transition-all duration-300"
            >
              <div className={`mb-5 flex h-11 w-11 items-center justify-center rounded-xl ${f.bg}`}>
                <f.icon className={`h-5 w-5 ${f.color}`} />
              </div>
              <h3 className="text-base font-bold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function HowItWorksSection() {
  const steps = [
    { num: "01", title: "Connect & import", desc: "Bring feedback in via CSV, a webhook endpoint, or connectors — qualitative and quantitative, normalized into one stream." },
    { num: "02", title: "Enrich & synthesize", desc: "AI scores each signal for sentiment, theme and urgency, then clusters related signals into insights with cross-signal severity." },
    { num: "03", title: "Govern & act", desc: "Rules propose actions and resolve conflicts; low-risk ones run automatically, high-risk ones wait for human approval — all audited." },
    { num: "04", title: "Measure the outcome", desc: "Each action's outcome contract checks whether the issue actually improved — operational, customer, and outcome closure." },
    { num: "05", title: "Remember what worked", desc: "Outcomes become searchable learnings whose confidence decays over time, ready to inform the next decision." },
  ];

  return (
    <section id="how-it-works" className="py-32 bg-card">
      <div className="mx-auto max-w-4xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-20"
        >
          <motion.p variants={fadeUp} custom={0} className="text-sm font-semibold text-primary uppercase tracking-widest">
            How It Works
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1} className="mt-3 text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Five steps to close the loop
          </motion.h2>
        </motion.div>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-border hidden md:block" />

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-50px" }}
            variants={stagger}
            className="space-y-12"
          >
            {steps.map((s, i) => (
              <motion.div key={i} variants={fadeUp} custom={i} className="flex gap-6 md:gap-10">
                <div className="relative z-10 flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-border bg-background text-2xl font-extrabold text-primary font-mono">
                  {s.num}
                </div>
                <div className="pt-2">
                  <h3 className="text-xl font-bold text-foreground mb-1.5">{s.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function SocialProofSection() {
  const stats = [
    { value: "<30%", label: "of firms systematically act on the feedback they collect" },
    { value: "48%", label: "follow up with dissatisfied customers" },
    { value: "0", label: "leading VoC tools ship an A/B-learning memory" },
    { value: "1 loop", label: "Signal → Insight → Action → Learning, governed end to end" },
  ];

  const differentiators = [
    {
      title: "Governed action, not just analytics",
      desc: "Most tools stop at a dashboard. Odradek drafts the action, resolves rule conflicts, and clears it through human approval before anything fires.",
    },
    {
      title: "Outcome-linked loop closure",
      desc: "“Closed loop” shouldn't just mean a ticket was created. Every action carries a metric and a window, so you can show the issue actually improved.",
    },
    {
      title: "A memory that compounds",
      desc: "The experiment learning repository remembers what worked, lets confidence decay as it ages, and resurfaces relevant learnings — so teams stop re-running the same tests.",
    },
  ];

  return (
    <section id="proof" className="py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUp} custom={0} className="text-sm font-semibold text-primary uppercase tracking-widest">
            Why Odradek
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1} className="mt-3 text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Built for the gap others leave open
          </motion.h2>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
          className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-20"
        >
          {stats.map((s, i) => (
            <motion.div key={i} variants={fadeUp} custom={i} className="text-center p-6 rounded-2xl border border-border bg-card">
              <div className="text-4xl font-extrabold text-primary font-mono">{s.value}</div>
              <div className="mt-2 text-sm text-muted-foreground">{s.label}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* Differentiators */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {differentiators.map((d, i) => (
            <motion.div
              key={i}
              variants={fadeUp}
              custom={i}
              className="rounded-2xl border border-border bg-card p-7 flex flex-col"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <CheckCircle2 className="h-5 w-5 text-primary" />
              </div>
              <h3 className="text-base font-bold text-foreground mb-2">{d.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed flex-1">{d.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function PricingSection() {
  const plans = [
    {
      name: "Starter",
      price: "$79",
      period: "/mo",
      description: "For growing teams getting started with feedback intelligence.",
      features: [
        "Up to 5,000 signals/month",
        "CSV + webhook ingestion",
        "AI triage & insight synthesis",
        "Rule builder with approvals",
        "Experiment learnings repository",
        "1 workspace",
      ],
      cta: "Start Free Trial",
      variant: "outline" as const,
      highlight: false,
    },
    {
      name: "Pro",
      price: "$249",
      period: "/mo",
      description: "For teams that need the full feedback loop with automation.",
      features: [
        "Unlimited signals",
        "All connectors + webhooks",
        "AI synthesis with cross-signal severity",
        "Governed action engine (conflict resolution + audit)",
        "Closed-loop outcome measurement",
        "EU AI Act + GDPR compliance checker",
        "5 workspaces",
      ],
      cta: "Start Free Trial",
      variant: "default" as const,
      highlight: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "",
      description: "For organizations with complex needs and compliance requirements.",
      features: [
        "Everything in Pro",
        "Self-hosted / EU data residency",
        "Bring-your-own model (local or API)",
        "SSO & SAML",
        "Custom SLAs & dedicated support",
        "Custom connectors",
        "Unlimited workspaces",
      ],
      cta: "Book a Demo",
      variant: "outline" as const,
      highlight: false,
    },
  ];

  return (
    <section id="pricing" className="py-32">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-16"
        >
          <motion.p variants={fadeUp} custom={0} className="text-sm font-semibold text-primary uppercase tracking-widest">
            Pricing
          </motion.p>
          <motion.h2 variants={fadeUp} custom={1} className="mt-3 text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Simple, transparent pricing
          </motion.h2>
          <motion.p variants={fadeUp} custom={2} className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            14-day free trial on all plans. No credit card required.
          </motion.p>
        </motion.div>

        {/* Pricing cards */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          variants={stagger}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20"
        >
          {plans.map((plan, i) => (
            <motion.div
              key={i}
              variants={fadeUp}
              custom={i}
              className={`relative rounded-2xl border p-8 flex flex-col ${
                plan.highlight
                  ? "border-primary bg-card shadow-xl shadow-primary/10 scale-[1.02]"
                  : "border-border bg-card"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-primary px-4 py-1 text-xs font-semibold text-primary-foreground">
                  Most Popular
                </div>
              )}
              <h3 className="text-lg font-bold text-foreground">{plan.name}</h3>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold text-foreground font-mono">{plan.price}</span>
                {plan.period && <span className="text-sm text-muted-foreground">{plan.period}</span>}
              </div>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{plan.description}</p>
              <ul className="mt-6 space-y-3 flex-1">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-start gap-2.5 text-sm text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link to="/auth" className="mt-8">
                <Button variant={plan.variant} size="lg" className="w-full h-11 font-semibold">
                  {plan.cta}
                </Button>
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Impact & B Corp section */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          variants={stagger}
          className="relative rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/5 via-card to-success/5 p-10 md:p-14 overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-primary/5 blur-[80px] -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-success/5 blur-[60px] translate-y-1/2 -translate-x-1/2" />

          <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
            <div>
              <motion.div variants={fadeUp} custom={0} className="inline-flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-4 py-1.5 text-xs font-semibold text-success mb-6">
                <Globe className="h-3.5 w-3.5" />
                Impact Program
              </motion.div>
              <motion.h3 variants={fadeUp} custom={1} className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight leading-tight">
                Free for impact startups.
                <br />
                <span className="text-primary">Deep discounts for B Corps.</span>
              </motion.h3>
              <motion.p variants={fadeUp} custom={2} className="mt-4 text-muted-foreground leading-relaxed max-w-lg">
                We believe organizations building a better world deserve the best tools without the enterprise price tag.
                If you're a certified B Corporation or an impact-driven startup, we want to support your mission.
              </motion.p>
            </div>

            <div>
              <motion.div variants={fadeUp} custom={3} className="space-y-5">
                <div className="rounded-xl border border-border bg-background/80 backdrop-blur-sm p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
                      <Sparkles className="h-5 w-5 text-success" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-foreground">Impact Startups</h4>
                      <p className="text-xs text-muted-foreground">Social enterprises & nonprofits</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Full Pro plan access at <span className="font-bold text-success">no cost</span> for qualifying impact startups,
                    social enterprises, and registered nonprofits. Apply and get approved in 48 hours.
                  </p>
                </div>

                <div className="rounded-xl border border-border bg-background/80 backdrop-blur-sm p-6">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <Shield className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-foreground">Certified B Corporations</h4>
                      <p className="text-xs text-muted-foreground">Verified B Corp certification</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    <span className="font-bold text-primary">50–80% discount</span> on any plan, scaled to your B Impact Assessment score.
                    Higher scores unlock deeper discounts. Because doing good should be rewarded.
                  </p>
                </div>

                <a href="mailto:impact@odradek.io">
                  <Button size="lg" className="w-full h-12 font-semibold gap-2 mt-2">
                    Apply for Impact Pricing <ArrowRight className="h-4 w-4" />
                  </Button>
                </a>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function ResponsibleAILearningsSection() {
  const resources = [
    {
      title: "EU AI Act Overview",
      url: "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
      description: "Official EU documentation on the AI Act regulatory framework",
      type: "Official Docs",
    },
    {
      title: "IEEE Ethically Aligned Design",
      url: "https://ethicsinaction.ieee.org/",
      description: "Comprehensive framework for autonomous and intelligent systems",
      type: "Framework",
    },
    {
      title: "AI Ethics Guidelines Global Inventory",
      url: "https://algorithmwatch.org/en/ai-ethics-guidelines-global-inventory/",
      description: "Database of AI ethics guidelines from around the world",
      type: "Research",
    },
    {
      title: "NIST AI Risk Management Framework",
      url: "https://www.nist.gov/itl/ai-risk-management-framework",
      description: "US standards for managing risks in AI systems",
      type: "Framework",
    },
  ];

  const reflections = [
    {
      title: "The Transparency Paradox",
      content: "The more we demand algorithmic transparency, the more we realize that true explainability often requires simplifying models to the point of reduced accuracy. The question becomes: what tradeoffs are we willing to accept?",
    },
    {
      title: "Beyond Bias Detection",
      content: "Bias in AI isn't just a technical problem—it's a mirror reflecting societal inequities. Technical fixes alone can't solve systemic issues; we need interdisciplinary approaches combining engineering, ethics, and policy.",
    },
    {
      title: "Accountability in Distributed Systems",
      content: "When an AI system fails, who's responsible? The data scientist? The company? The regulator who approved it? Responsible AI requires new frameworks for distributed accountability.",
    },
  ];

  const researchTopics = [
    {
      title: "Algorithmic Auditing Methods",
      status: "Ongoing",
      description: "Exploring technical and procedural approaches to auditing AI systems for fairness, accountability, and transparency.",
    },
    {
      title: "Consent Mechanisms in ML Pipelines",
      status: "Completed",
      description: "Investigating how informed consent can be meaningfully implemented throughout the machine learning lifecycle.",
    },
    {
      title: "Environmental Impact of Large Language Models",
      status: "Ongoing",
      description: "Quantifying carbon footprints and exploring sustainable alternatives for training and deploying LLMs.",
    },
    {
      title: "Human-AI Collaboration Patterns",
      status: "Planned",
      description: "Studying optimal patterns for human oversight in AI-assisted decision-making systems.",
    },
  ];

  const classNotes = [
    {
      module: "Ethics & Governance",
      topics: ["Stakeholder theory in AI", "Regulatory landscapes (EU, US, China)", "Self-regulation vs. hard law"],
      keyInsight: "Effective AI governance requires multi-stakeholder engagement, not just top-down regulation.",
    },
    {
      module: "Technical Fairness",
      topics: ["Fairness metrics (demographic parity, equalized odds)", "Bias mitigation techniques", "Fairness-accuracy tradeoffs"],
      keyInsight: "There's no single definition of fairness—context determines which metric matters most.",
    },
    {
      module: "Explainability & Trust",
      topics: ["LIME, SHAP, attention mechanisms", "Human factors in explanations", "Trust calibration"],
      keyInsight: "Explanations must be tailored to the audience; technical accuracy doesn't equal understandability.",
    },
    {
      module: "Privacy & Data Rights",
      topics: ["Differential privacy", "Federated learning", "Data minimization principles"],
      keyInsight: "Privacy-preserving ML is possible but requires intentional architecture decisions from the start.",
    },
  ];

  return (
    <section id="learnings" className="py-32 bg-card">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={stagger}
          className="text-center mb-16"
        >
          <motion.div variants={fadeUp} custom={0} className="inline-flex items-center gap-2 rounded-full border border-info/30 bg-info/10 px-4 py-1.5 text-xs font-semibold text-info mb-6">
            <GraduationCap className="h-3.5 w-3.5" />
            Master's Research
          </motion.div>
          <motion.h2 variants={fadeUp} custom={1} className="text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Responsible AI Learnings
          </motion.h2>
          <motion.p variants={fadeUp} custom={2} className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            Insights and reflections from my master's research on ethical AI development, governance frameworks, and technical fairness.
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-50px" }}
          variants={fadeUp}
          custom={0}
        >
          <Tabs defaultValue="resources" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-8">
              <TabsTrigger value="resources" className="gap-2">
                <ExternalLink className="h-4 w-4" />
                <span className="hidden sm:inline">Resources</span>
              </TabsTrigger>
              <TabsTrigger value="reflections" className="gap-2">
                <Quote className="h-4 w-4" />
                <span className="hidden sm:inline">Reflections</span>
              </TabsTrigger>
              <TabsTrigger value="research" className="gap-2">
                <Brain className="h-4 w-4" />
                <span className="hidden sm:inline">Research</span>
              </TabsTrigger>
              <TabsTrigger value="notes" className="gap-2">
                <FileText className="h-4 w-4" />
                <span className="hidden sm:inline">Class Notes</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="resources" className="mt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {resources.map((r, i) => (
                  <a
                    key={i}
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group rounded-xl border border-border bg-background p-6 hover:border-primary/30 hover:shadow-lg transition-all duration-300"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-semibold text-primary">
                        {r.type}
                      </span>
                      <ExternalLink className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                    <h3 className="text-base font-bold text-foreground mb-2 group-hover:text-primary transition-colors">
                      {r.title}
                    </h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {r.description}
                    </p>
                  </a>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="reflections" className="mt-0">
              <div className="space-y-6">
                {reflections.map((r, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-border bg-background p-8 relative overflow-hidden"
                  >
                    <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary via-info to-primary" />
                    <Quote className="absolute top-4 right-4 h-12 w-12 text-muted/20" />
                    <h3 className="text-lg font-bold text-foreground mb-4 pl-4">{r.title}</h3>
                    <p className="text-muted-foreground leading-relaxed pl-4 italic">
                      "{r.content}"
                    </p>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="research" className="mt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {researchTopics.map((r, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-border bg-background p-6"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                        r.status === "Completed" 
                          ? "bg-success/10 text-success" 
                          : r.status === "Ongoing"
                          ? "bg-warning/10 text-warning"
                          : "bg-muted text-muted-foreground"
                      }`}>
                        {r.status}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-foreground mb-2">{r.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{r.description}</p>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="notes" className="mt-0">
              <div className="space-y-4">
                {classNotes.map((note, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-border bg-background p-6"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-info/10">
                        <BookOpen className="h-5 w-5 text-info" />
                      </div>
                      <h3 className="text-lg font-bold text-foreground">{note.module}</h3>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
                      {note.topics.map((topic, j) => (
                        <span
                          key={j}
                          className="inline-flex items-center rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground"
                        >
                          {topic}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-start gap-2 p-4 rounded-lg bg-primary/5 border border-primary/10">
                      <Lightbulb className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                      <p className="text-sm text-foreground">
                        <span className="font-semibold">Key Insight:</span> {note.keyInsight}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="py-32">
      <div className="mx-auto max-w-3xl px-6 text-center">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
        >
          <motion.h2 variants={fadeUp} custom={0} className="text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            Ready to close the loop?
          </motion.h2>
          <motion.p variants={fadeUp} custom={1} className="mt-4 text-lg text-muted-foreground max-w-xl mx-auto">
            Import a CSV or connect a source and watch the loop close — from signal to triaged insight, governed action, and measured outcome.
          </motion.p>
          <motion.div variants={fadeUp} custom={2} className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/auth">
              <Button size="lg" className="h-12 px-10 text-base font-semibold gap-2">
                Start Free Trial <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Button variant="outline" size="lg" className="h-12 px-10 text-base font-semibold">
              Book a Demo
            </Button>
          </motion.div>
          <motion.div variants={fadeUp} custom={3} className="mt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-success" /> Human-in-the-loop</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-success" /> Self-hostable</span>
            <span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5 text-success" /> Setup in minutes</span>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
                <span className="text-xs font-bold text-primary-foreground">O</span>
              </div>
              <span className="text-sm font-bold text-foreground">Odradek</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              AI-powered customer feedback intelligence that closes the loop.
            </p>
          </div>
          {[
            { title: "Product", links: ["Features", "Pricing", "Integrations", "Changelog"] },
            { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
            { title: "Legal", links: ["Privacy", "Terms", "Security", "GDPR"] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-xs text-muted-foreground hover:text-foreground transition-colors">{link}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">© 2026 Odradek. All rights reserved.</p>
          <div className="flex gap-4 text-xs text-muted-foreground">
            <a href="#" className="hover:text-foreground transition-colors">Twitter</a>
            <a href="#" className="hover:text-foreground transition-colors">LinkedIn</a>
            <a href="#" className="hover:text-foreground transition-colors">GitHub</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

const Landing = () => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Navbar />
      <HeroSection />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PricingSection />
      <SocialProofSection />
      <ResponsibleAILearningsSection />
      <CTASection />
      <Footer />
    </div>
  );
};

export default Landing;
