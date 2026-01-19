import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    FileText,
    MessageSquare,
    ClipboardCheck,
    CalendarDays,
    Upload,
    Search,
    CheckCircle2,
    AlertTriangle,
    Loader2,
    ExternalLink,
    Plus,
    RefreshCcw,
} from "lucide-react";


const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Guideline — Rapid Prototype (Canvas)
 * Single-file React app with:
 * - Left-nav layout
 * - Pages: Chat, Policies (Ingest), Review Queue, Schedule
 * - Real API integration replacing mock
 */

// -----------------------------
// Types
// -----------------------------

type AccessLevel = "public" | "internal" | "confidential" | "restricted";

type Doc = {
    id: string;
    title: string;
    policyKey: string;
    effectiveDate: string; // YYYY-MM-DD
    access: AccessLevel;
    tags: string[];
    chunks: Chunk[];
    created_at: number;
};

type ChunkType = "text" | "table";

type Chunk = {
    id: string;
    docId: string;
    chunkIndex: number;
    type: ChunkType;
    pageStart: number;
    pageEnd: number;
    sectionTitle?: string;
    content: string; // markdown-ish
    access: AccessLevel;
    effectiveDate: string;
};

type Citation = {
    chunkId: string;
    docId: string;
    docTitle: string;
    pageStart: number;
    pageEnd: number;
    quote: string;
    distance: number;
};

type Confidence = "High" | "Medium" | "Low";

type QAAnswer = {
    answer: string;
    citations: Citation[];
    confidence: Confidence;
    bestDistance: number;
    lowConfidence: boolean;
    reviewId?: string;
};

type ReviewStatus = "open" | "resolved";

type ReviewItem = {
    id: string;
    question: string;
    createdAt: number;
    reason: "low_confidence" | "not_found" | "conflict";
    status: ReviewStatus;
    draftAnswer?: string;
    draftCitations: Citation[];
    finalAnswer?: string;
    resolvedAt?: number;
};

type ScheduleConfig = {
    timezone: string;
    week: Array<{ day: string; start: string; end: string; note?: string }>;
    oncall?: Array<{ from: string; to: string; note?: string }>;
    holidays?: Array<{ date: string; name: string }>;
};

// -----------------------------
// Helpers
// -----------------------------

function formatTime(ts: number) {
    const d = new Date(ts);
    return d.toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function classNames(...xs: Array<string | false | undefined | null>) {
    return xs.filter(Boolean).join(" ");
}

// -----------------------------
// API Hook (Real Fetch)
// -----------------------------

function useHttpApi() {
    const api = useMemo(() => {
        return {
            async health() {
                const res = await fetch(`${BASE}/health`);
                return res.json();
            },
            async listDocs() {
                const res = await fetch(`${BASE}/docs`);
                return res.json();
            },
            async ingestDoc(input: {
                title: string;
                policyKey: string;
                effectiveDate: string;
                access: AccessLevel;
                tags: string[];
                content: string;
            }) {
                const res = await fetch(`${BASE}/ingest`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(input)
                });
                return res.json();
            },
            async askPolicy(input: { userId: string; role: AccessLevel; question: string }): Promise<QAAnswer> {
                const res = await fetch(`${BASE}/chat/ask`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(input)
                });
                return res.json();
            },
            async listReview(status?: ReviewStatus) {
                let url = `${BASE}/review`;
                if (status) url += `?status=${status}`;
                const res = await fetch(url);
                return res.json();
            },
            async resolveReview(id: string, finalAnswer: string, promoteToFaq: boolean) {
                const res = await fetch(`${BASE}/review/${id}/resolve`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ finalAnswer, promoteToFaq })
                });
                if (!res.ok) throw new Error("Failed to resolve");
                return res.json();
            },
            async getSchedule() {
                const res = await fetch(`${BASE}/schedule`);
                return res.json();
            },
            async setSchedule(next: ScheduleConfig) {
                const res = await fetch(`${BASE}/schedule`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(next)
                });
                if (!res.ok) throw new Error("Failed to set schedule");
                return res.json();
            },
            async askSchedule(question: string) {
                const res = await fetch(`${BASE}/schedule/ask`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question })
                });
                return res.json();
            },
        };
    }, []);

    return { api };
}


// -----------------------------
// UI Building Blocks
// -----------------------------

function Pill({ tone, children }: { tone: "ok" | "warn" | "bad" | "neutral"; children: React.ReactNode }) {
    const styles =
        tone === "ok"
            ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
            : tone === "warn"
                ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                : tone === "bad"
                    ? "bg-rose-500/10 text-rose-300 border-rose-500/20"
                    : "bg-slate-500/10 text-slate-300 border-slate-500/20";
    return <span className={classNames("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs", styles)}>{children}</span>;
}

function Card({ children, className }: { children: React.ReactNode; className?: string }) {
    return <div className={classNames("rounded-2xl border border-slate-800 bg-slate-950/60 shadow-sm", className)}>{children}</div>;
}

function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
    return (
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-4 py-3">
            <div>
                <div className="text-sm font-semibold text-slate-100">{title}</div>
                {subtitle ? <div className="mt-0.5 text-xs text-slate-400">{subtitle}</div> : null}
            </div>
            {right ? <div className="flex items-center gap-2">{right}</div> : null}
        </div>
    );
}

function Button({
    children,
    onClick,
    disabled,
    variant = "primary",
    className,
    title,
}: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    variant?: "primary" | "secondary" | "ghost" | "danger";
    className?: string;
    title?: string;
}) {
    const base = "inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition";
    const styles =
        variant === "primary"
            ? "bg-slate-100 text-slate-900 hover:bg-white"
            : variant === "secondary"
                ? "bg-slate-900 text-slate-100 border border-slate-800 hover:bg-slate-800"
                : variant === "danger"
                    ? "bg-rose-600 text-white hover:bg-rose-500"
                    : "text-slate-200 hover:bg-slate-900";

    return (
        <button
            title={title}
            disabled={disabled}
            onClick={onClick}
            className={classNames(base, styles, disabled ? "opacity-50 cursor-not-allowed" : "", className)}
        >
            {children}
        </button>
    );
}

function Input({ value, onChange, placeholder, className }: { value: string; onChange: (v: string) => void; placeholder?: string; className?: string }) {
    return (
        <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={classNames(
                "w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-700",
                className
            )}
        />
    );
}

function Textarea({
    value,
    onChange,
    placeholder,
    rows = 6,
    className,
}: {
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
    rows?: number;
    className?: string;
}) {
    return (
        <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={rows}
            className={classNames(
                "w-full resize-none rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-700",
                className
            )}
        />
    );
}

function Select({
    value,
    onChange,
    options,
    className,
}: {
    value: string;
    onChange: (v: string) => void;
    options: Array<{ label: string; value: string }>;
    className?: string;
}) {
    return (
        <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={classNames(
                "w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-700",
                className
            )}
        >
            {options.map((o) => (
                <option key={o.value} value={o.value}>
                    {o.label}
                </option>
            ))}
        </select>
    );
}

function Divider() {
    return <div className="h-px w-full bg-slate-800" />;
}

// -----------------------------
// Main App
// -----------------------------

type Page = "chat" | "policies" | "review" | "schedule";

export default function App() {
    const { api } = useHttpApi();
    const [page, setPage] = useState<Page>("chat");
    const [healthy, setHealthy] = useState<"unknown" | "ok" | "bad">("unknown");

    useEffect(() => {
        let alive = true;
        api
            .health()
            .then(() => alive && setHealthy("ok"))
            .catch(() => alive && setHealthy("bad"));
        return () => {
            alive = false;
        };
    }, [api]);

    const nav = [
        { id: "chat" as const, label: "Chat", icon: MessageSquare },
        { id: "policies" as const, label: "Policies", icon: FileText },
        { id: "review" as const, label: "Review Queue", icon: ClipboardCheck },
        { id: "schedule" as const, label: "Schedule", icon: CalendarDays },
    ];

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100">
            <div className="mx-auto flex min-h-screen max-w-7xl">
                {/* Sidebar */}
                <aside className="hidden w-72 border-r border-slate-900 bg-slate-950/80 p-4 md:block">
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="text-lg font-semibold tracking-tight">Guideline</div>
                            <div className="text-xs text-slate-400">Prototype • No Auth</div>
                        </div>
                        <Pill tone={healthy === "ok" ? "ok" : healthy === "bad" ? "bad" : "neutral"}>
                            <span className="inline-block h-2 w-2 rounded-full bg-current" />
                            {healthy === "ok" ? "API Healthy" : healthy === "bad" ? "API Down" : "Checking"}
                        </Pill>
                    </div>

                    <div className="mt-6 space-y-1">
                        {nav.map((n) => {
                            const Icon = n.icon;
                            const active = page === n.id;
                            return (
                                <button
                                    key={n.id}
                                    onClick={() => setPage(n.id)}
                                    className={classNames(
                                        "flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-sm transition",
                                        active ? "bg-slate-900 text-white" : "text-slate-300 hover:bg-slate-900/60"
                                    )}
                                >
                                    <Icon className="h-4 w-4" />
                                    {n.label}
                                </button>
                            );
                        })}
                    </div>

                    <div className="mt-6">
                        <Card className="overflow-hidden">
                            <CardHeader
                                title="Demo tips"
                                subtitle="Use these questions to show citations + escalation"
                            />
                            <div className="space-y-2 p-3 text-xs text-slate-300">
                                <div className="rounded-xl bg-slate-900/60 p-2">“Do I need receipts for expenses?”</div>
                                <div className="rounded-xl bg-slate-900/60 p-2">“What’s the meals limit?”</div>
                                <div className="rounded-xl bg-slate-900/60 p-2">“Can I expense Uber to the airport?”</div>
                                <div className="rounded-xl bg-slate-900/60 p-2">“What’s my schedule Monday?”</div>
                            </div>
                        </Card>
                    </div>
                </aside>

                {/* Main */}
                <main className="flex-1 p-4 md:p-6">
                    <TopBar page={page} setPage={setPage} healthy={healthy} />
                    <div className="mt-4">
                        <AnimatePresence mode="wait">
                            {page === "chat" && (
                                <motion.div key="chat" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                                    <ChatPage api={api} onGoReview={() => setPage("review")} onGoSchedule={() => setPage("schedule")} />
                                </motion.div>
                            )}
                            {page === "policies" && (
                                <motion.div key="policies" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                                    <PoliciesPage api={api} />
                                </motion.div>
                            )}
                            {page === "review" && (
                                <motion.div key="review" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                                    <ReviewPage api={api} />
                                </motion.div>
                            )}
                            {page === "schedule" && (
                                <motion.div key="schedule" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                                    <SchedulePage api={api} />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </div>
    );
}

function TopBar({
    page,
    setPage,
    healthy,
}: {
    page: Page;
    setPage: (p: Page) => void;
    healthy: "unknown" | "ok" | "bad";
}) {
    const title =
        page === "chat" ? "Chat" : page === "policies" ? "Policies" : page === "review" ? "Review Queue" : "Schedule";

    return (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
                <div className="text-xl font-semibold tracking-tight">{title}</div>
                <div className="text-sm text-slate-400">Internal assistant for schedule + policy answers with citations and escalation.</div>
            </div>
            <div className="flex items-center gap-2">
                <div className="md:hidden">
                    <Select
                        value={page}
                        onChange={(v) => setPage(v as Page)}
                        options={[
                            { label: "Chat", value: "chat" },
                            { label: "Policies", value: "policies" },
                            { label: "Review Queue", value: "review" },
                            { label: "Schedule", value: "schedule" },
                        ]}
                    />
                </div>
                <Pill tone={healthy === "ok" ? "ok" : healthy === "bad" ? "bad" : "neutral"}>
                    {healthy === "ok" ? <CheckCircle2 className="h-3.5 w-3.5" /> : healthy === "bad" ? <AlertTriangle className="h-3.5 w-3.5" /> : <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                    {healthy === "ok" ? "Ready" : healthy === "bad" ? "Offline" : "Checking"}
                </Pill>
            </div>
        </div>
    );
}

// -----------------------------
// Chat Page
// -----------------------------

type ChatMsg =
    | { id: string; role: "user"; text: string; at: number }
    | { id: string; role: "assistant"; text: string; at: number; answer?: QAAnswer };

function uid(prefix = "id") {
    return `${prefix}_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`;
}

function ChatPage({ api, onGoReview, onGoSchedule }: { api: any; onGoReview: () => void; onGoSchedule: () => void }) {
    const [role, setRole] = useState<AccessLevel>("internal");
    const [userId, setUserId] = useState("demo_user");
    const [input, setInput] = useState("");
    const [busy, setBusy] = useState(false);
    const [msgs, setMsgs] = useState<ChatMsg[]>(() => [
        {
            id: uid("m"),
            role: "assistant",
            text: "Ask me about a company policy (with citations) or your work schedule. If I’m not confident, I’ll route it to the Review Queue.",
            at: Date.now() - 1000 * 30,
        },
    ]);

    const bottomRef = useRef<HTMLDivElement | null>(null);
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [msgs.length]);

    async function send() {
        const q = input.trim();
        if (!q || busy) return;
        setInput("");
        setBusy(true);

        const userMsg: ChatMsg = { id: uid("m"), role: "user", text: q, at: Date.now() };
        setMsgs((prev) => [...prev, userMsg]);

        // Decide route: schedule vs policy
        const isSchedule = /schedule|shift|on[- ]?call|holiday|availability|hours/i.test(q);

        try {
            if (isSchedule) {
                const res = await api.askSchedule(q);
                const a: ChatMsg = {
                    id: uid("m"),
                    role: "assistant",
                    text: res.answer,
                    at: Date.now(),
                };
                setMsgs((prev) => [...prev, a]);
            } else {
                const ans: QAAnswer = await api.askPolicy({ userId, role, question: q });
                const a: ChatMsg = {
                    id: uid("m"),
                    role: "assistant",
                    text: ans.answer,
                    at: Date.now(),
                    answer: ans,
                };
                setMsgs((prev) => [...prev, a]);
            }
        } finally {
            setBusy(false);
        }
    }

    const quick = [
        "Do I need receipts for expenses?",
        "What’s the meals limit?",
        "Can I expense Uber to the airport?",
        "What’s my schedule Monday?",
        "What’s the hotel limit?",
    ];

    return (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Conversation */}
            <Card className="lg:col-span-2">
                <CardHeader
                    title="Chat"
                    subtitle="Policy answers include citations + confidence. Low-confidence escalates automatically."
                    right={
                        <div className="flex items-center gap-2">
                            <Pill tone="neutral">No Auth</Pill>
                        </div>
                    }
                />

                <div className="h-[560px] overflow-y-auto p-4">
                    <div className="space-y-3">
                        {msgs.map((m) => (
                            <div key={m.id} className={classNames("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                                <div className={classNames("max-w-[85%] rounded-2xl border px-3 py-2", m.role === "user" ? "border-slate-800 bg-slate-900" : "border-slate-800 bg-slate-950")}
                                >
                                    <div className="text-xs text-slate-500">{m.role === "user" ? userId : "Guideline"} • {formatTime(m.at)}</div>
                                    <div className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-slate-100">
                                        <RichText text={m.text} />
                                    </div>

                                    {m.role === "assistant" && m.answer ? (
                                        <div className="mt-3 space-y-3">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <ConfidencePill confidence={m.answer.confidence} bestDistance={m.answer.bestDistance} />
                                                {m.answer.lowConfidence ? (
                                                    <Pill tone="warn">
                                                        <AlertTriangle className="h-3.5 w-3.5" />
                                                        Routed to Review
                                                    </Pill>
                                                ) : (
                                                    <Pill tone="ok">
                                                        <CheckCircle2 className="h-3.5 w-3.5" />
                                                        Verified by sources
                                                    </Pill>
                                                )}
                                                {m.answer.reviewId ? (
                                                    <Button variant="ghost" onClick={onGoReview}>
                                                        <ClipboardCheck className="h-4 w-4" />
                                                        Open Review
                                                    </Button>
                                                ) : null}
                                            </div>

                                            <Citations citations={m.answer.citations} />
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        ))}
                        <div ref={bottomRef} />
                    </div>
                </div>

                <Divider />

                <div className="space-y-3 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <div className="text-xs text-slate-400">Quick prompts:</div>
                        {quick.map((q) => (
                            <button
                                key={q}
                                onClick={() => setInput(q)}
                                className="rounded-full border border-slate-800 bg-slate-950 px-3 py-1 text-xs text-slate-200 hover:bg-slate-900"
                            >
                                {q}
                            </button>
                        ))}
                    </div>

                    <div className="flex flex-col gap-2 md:flex-row md:items-end">
                        <div className="flex-1">
                            <Textarea value={input} onChange={setInput} rows={3} placeholder="Ask a question…" />
                        </div>
                        <div className="flex w-full gap-2 md:w-auto">
                            <Button variant="secondary" onClick={onGoSchedule}>
                                <CalendarDays className="h-4 w-4" />
                                Schedule
                            </Button>
                            <Button onClick={send} disabled={busy || !input.trim()}>
                                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquare className="h-4 w-4" />}
                                Send
                            </Button>
                        </div>
                    </div>
                </div>
            </Card>

            {/* Settings */}
            <div className="space-y-4">
                <Card>
                    <CardHeader title="Session" subtitle="Simulate different access levels" />
                    <div className="space-y-3 p-4">
                        <div>
                            <div className="mb-1 text-xs text-slate-400">User ID</div>
                            <Input value={userId} onChange={setUserId} placeholder="demo_user" />
                        </div>
                        <div>
                            <div className="mb-1 text-xs text-slate-400">Role / Access Level</div>
                            <Select
                                value={role}
                                onChange={(v) => setRole(v as AccessLevel)}
                                options={[
                                    { label: "Public", value: "public" },
                                    { label: "Internal", value: "internal" },
                                    { label: "Confidential", value: "confidential" },
                                    { label: "Restricted", value: "restricted" },
                                ]}
                            />
                            <div className="mt-2 text-xs text-slate-500">Used to filter which policy chunks can be retrieved.</div>
                        </div>
                    </div>
                </Card>

                <Card>
                    <CardHeader title="What this demo proves" subtitle="Mentor-grade requirements" />
                    <div className="space-y-2 p-4 text-sm text-slate-300">
                        <div className="flex items-start gap-2">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" />
                            <div>
                                <div className="font-medium text-slate-200">Citations</div>
                                <div className="text-xs text-slate-500">Answer includes doc + page + snippet.</div>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" />
                            <div>
                                <div className="font-medium text-slate-200">Permissions</div>
                                <div className="text-xs text-slate-500">Role filters retrieval (no metadata leakage).</div>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" />
                            <div>
                                <div className="font-medium text-slate-200">Versioning</div>
                                <div className="text-xs text-slate-500">Newest policy per key is preferred.</div>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-300" />
                            <div>
                                <div className="font-medium text-slate-200">Human-in-loop</div>
                                <div className="text-xs text-slate-500">Low confidence auto-routes to Review Queue.</div>
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}

function RichText({ text }: { text: string }) {
    // Minimal markdown-ish renderer for **bold**
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return (
        <>
            {parts.map((p, i) => {
                const m = p.match(/^\*\*([^*]+)\*\*$/);
                if (m) return (
                    <strong key={i} className="font-semibold text-slate-50">
                        {m[1]}
                    </strong>
                );
                return <span key={i}>{p}</span>;
            })}
        </>
    );
}

function ConfidencePill({ confidence, bestDistance }: { confidence: Confidence; bestDistance: number }) {
    const tone = confidence === "High" ? "ok" : confidence === "Medium" ? "warn" : "bad";
    return (
        <Pill tone={tone}>
            {confidence}
            <span className="text-slate-400">•</span>
            dist {bestDistance.toFixed(3)}
        </Pill>
    );
}

function Citations({ citations }: { citations: Citation[] }) {
    if (!citations || citations.length === 0) {
        return (
            <Card className="border-slate-900 bg-slate-950/40">
                <div className="p-3 text-xs text-slate-400">No citations available (nothing matched your access level).</div>
            </Card>
        );
    }
    return (
        <div className="space-y-2">
            <div className="text-xs font-medium text-slate-300">Sources</div>
            <div className="grid grid-cols-1 gap-2">
                {citations.map((c) => (
                    <Card key={c.chunkId} className="border-slate-900 bg-slate-950/40">
                        <div className="p-3">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <div className="text-xs font-semibold text-slate-200">{c.docTitle}</div>
                                    <div className="text-[11px] text-slate-500">p.{c.pageStart}{c.pageEnd !== c.pageStart ? `–${c.pageEnd}` : ""} • dist {c.distance.toFixed(3)}</div>
                                </div>
                                <Button variant="ghost" title="Open source (stub)">
                                    <ExternalLink className="h-4 w-4" />
                                </Button>
                            </div>
                            <div className="mt-2 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300">
                                {c.quote}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
}

// -----------------------------
// Policies Page
// -----------------------------

function PoliciesPage({ api }: { api: any }) {
    const [docs, setDocs] = useState<Doc[]>([]);
    const [loading, setLoading] = useState(false);

    const [title, setTitle] = useState("Expense Policy 2026");
    const [policyKey, setPolicyKey] = useState("expense_policy");
    const [effectiveDate, setEffectiveDate] = useState("2026-01-01");
    const [access, setAccess] = useState<AccessLevel>("internal");
    const [tags, setTags] = useState("expenses, finance");
    const [content, setContent] = useState(
        `Expense Policy (2026)\n\nReceipts\n- Expenses above $30 require a receipt.\n\nLimits\n| Category | Limit | Notes |\n|---|---:|---|\n| Meals | $70/day | Itemized receipt required |\n| Hotel | $250/night | Approval required for exceptions |\n\nEffective Date: 2026-01-01`
    );

    async function refresh() {
        setLoading(true);
        try {
            const res = await api.listDocs();
            setDocs(res);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        refresh();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    async function ingest() {
        if (!title.trim() || !policyKey.trim() || !effectiveDate.trim() || !content.trim()) return;
        setLoading(true);
        try {
            await api.ingestDoc({
                title: title.trim(),
                policyKey: policyKey.trim(),
                effectiveDate: effectiveDate.trim(),
                access,
                tags: tags
                    .split(",")
                    .map((t: string) => t.trim())
                    .filter(Boolean),
                content,
            });
            await refresh();
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
                <CardHeader title="Ingest policy" subtitle="Paste text or markdown (tables preserved)" right={<Pill tone="neutral">No PDF parsing in MVP</Pill>} />
                <div className="space-y-3 p-4">
                    <div>
                        <div className="mb-1 text-xs text-slate-400">Title</div>
                        <Input value={title} onChange={setTitle} />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <div className="mb-1 text-xs text-slate-400">Policy Key</div>
                            <Input value={policyKey} onChange={setPolicyKey} placeholder="travel_policy" />
                        </div>
                        <div>
                            <div className="mb-1 text-xs text-slate-400">Effective Date</div>
                            <Input value={effectiveDate} onChange={setEffectiveDate} placeholder="YYYY-MM-DD" />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <div className="mb-1 text-xs text-slate-400">Access</div>
                            <Select
                                value={access}
                                onChange={(v) => setAccess(v as AccessLevel)}
                                options={[
                                    { label: "Public", value: "public" },
                                    { label: "Internal", value: "internal" },
                                    { label: "Confidential", value: "confidential" },
                                    { label: "Restricted", value: "restricted" },
                                ]}
                            />
                        </div>
                        <div>
                            <div className="mb-1 text-xs text-slate-400">Tags</div>
                            <Input value={tags} onChange={setTags} placeholder="travel, expenses" />
                        </div>
                    </div>

                    <div>
                        <div className="mb-1 text-xs text-slate-400">Content</div>
                        <Textarea value={content} onChange={setContent} rows={10} />
                        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                            <Pill tone="neutral">Tip: include a markdown table</Pill>
                            <Pill tone="neutral">Chunking preserves table blocks</Pill>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <Button onClick={ingest} disabled={loading} className="flex-1">
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                            Ingest
                        </Button>
                        <Button variant="secondary" onClick={refresh} disabled={loading}>
                            <RefreshCcw className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </Card>

            <Card className="lg:col-span-2">
                <CardHeader
                    title="Policies"
                    subtitle="Newest per policy key is preferred during retrieval"
                    right={
                        <Pill tone="neutral">
                            <Search className="h-3.5 w-3.5" />
                            {docs.length} docs
                        </Pill>
                    }
                />
                <div className="p-4">
                    {loading && docs.length === 0 ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                        </div>
                    ) : docs.length === 0 ? (
                        <div className="text-sm text-slate-400">No documents yet.</div>
                    ) : (
                        <div className="space-y-2">
                            {docs.map((d) => (
                                <Card key={d.id} className="border-slate-900 bg-slate-950/40">
                                    <div className="p-3">
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <div className="text-sm font-semibold text-slate-100">{d.title}</div>
                                                <div className="mt-0.5 text-xs text-slate-500">
                                                    key <span className="text-slate-300">{d.policyKey}</span> • effective <span className="text-slate-300">{d.effectiveDate}</span> • access <span className="text-slate-300">{d.access}</span>
                                                </div>
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {d.tags.map((t) => (
                                                        <Pill key={t} tone="neutral">
                                                            {t}
                                                        </Pill>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-xs text-slate-500">Chunks</div>
                                                <div className="text-sm font-semibold">{d.chunks.length}</div>
                                                <div className="mt-1 text-[11px] text-slate-500">Added {formatTime(d.created_at)}</div>
                                            </div>
                                        </div>

                                        <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300">
                                            <div className="text-[11px] text-slate-500">Preview</div>
                                            <div className="mt-1 line-clamp-3 whitespace-pre-wrap">{d.chunks[0]?.content}</div>
                                        </div>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
}

// -----------------------------
// Review Page
// -----------------------------

function ReviewPage({ api }: { api: any }) {
    const [items, setItems] = useState<ReviewItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState<"open" | "resolved" | "all">("open");
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [finalAnswer, setFinalAnswer] = useState("");
    const [promote, setPromote] = useState(false);

    async function refresh() {
        setLoading(true);
        try {
            const res = await api.listReview(filter === "all" ? undefined : filter);
            setItems(res);
            if (!selectedId && res.length) setSelectedId(res[0].id);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        refresh();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filter]);

    const selected = items.find((x) => x.id === selectedId) || null;

    useEffect(() => {
        if (selected?.finalAnswer) setFinalAnswer(selected.finalAnswer);
        else setFinalAnswer(selected?.draftAnswer || "");
        setPromote(false);
    }, [selectedId]);

    async function resolve() {
        if (!selected || selected.status !== "open") return;
        if (!finalAnswer.trim()) return;
        setLoading(true);
        try {
            await api.resolveReview(selected.id, finalAnswer.trim(), promote);
            await refresh();
        } finally {
            setLoading(false);
        }
    }

    function reasonLabel(r: ReviewItem["reason"]) {
        if (r === "not_found") return "Not found";
        if (r === "conflict") return "Policy conflict";
        return "Low confidence";
    }

    return (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
                <CardHeader
                    title="Queue"
                    subtitle="Low-confidence questions routed here"
                    right={
                        <div className="flex items-center gap-2">
                            <Select
                                value={filter}
                                onChange={(v) => setFilter(v as any)}
                                options={[
                                    { label: "Open", value: "open" },
                                    { label: "Resolved", value: "resolved" },
                                    { label: "All", value: "all" },
                                ]}
                            />
                            <Button variant="secondary" onClick={refresh} disabled={loading}>
                                <RefreshCcw className="h-4 w-4" />
                            </Button>
                        </div>
                    }
                />
                <div className="p-3">
                    {loading && items.length === 0 ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
                        </div>
                    ) : items.length === 0 ? (
                        <div className="text-sm text-slate-400">No items in this view.</div>
                    ) : (
                        <div className="space-y-2">
                            {items.map((it) => (
                                <button
                                    key={it.id}
                                    onClick={() => setSelectedId(it.id)}
                                    className={classNames(
                                        "w-full rounded-2xl border p-3 text-left transition",
                                        selectedId === it.id ? "border-slate-700 bg-slate-900" : "border-slate-900 bg-slate-950/40 hover:bg-slate-900/40"
                                    )}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="text-xs font-semibold text-slate-200">{reasonLabel(it.reason)}</div>
                                        <Pill tone={it.status === "open" ? "warn" : "ok"}>{it.status}</Pill>
                                    </div>
                                    <div className="mt-1 line-clamp-2 text-sm text-slate-100">{it.question}</div>
                                    <div className="mt-2 text-[11px] text-slate-500">{formatTime(it.createdAt)}</div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </Card>

            <Card className="lg:col-span-2">
                <CardHeader
                    title="Review"
                    subtitle={selected ? `Item ${selected.id.slice(0, 10)}… • ${reasonLabel(selected.reason)}` : "Select an item"}
                    right={
                        selected ? (
                            <Pill tone={selected.status === "open" ? "warn" : "ok"}>
                                {selected.status === "open" ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                                {selected.status}
                            </Pill>
                        ) : null
                    }
                />

                <div className="p-4">
                    {!selected ? (
                        <div className="text-sm text-slate-400">Pick a queue item to review.</div>
                    ) : (
                        <div className="space-y-4">
                            <div>
                                <div className="text-xs font-medium text-slate-300">Question</div>
                                <div className="mt-2 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-100">
                                    {selected.question}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                <div>
                                    <div className="text-xs font-medium text-slate-300">System draft</div>
                                    <div className="mt-2 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200">
                                        {selected.draftAnswer ? <RichText text={selected.draftAnswer} /> : <span className="text-slate-500">No draft (not found / too uncertain)</span>}
                                    </div>
                                    <div className="mt-2 text-xs text-slate-500">Use this as a starting point, then finalize below.</div>
                                </div>

                                <div>
                                    <div className="text-xs font-medium text-slate-300">Top sources</div>
                                    <div className="mt-2">
                                        <Citations citations={selected.draftCitations} />
                                    </div>
                                </div>
                            </div>

                            <div>
                                <div className="flex items-center justify-between">
                                    <div className="text-xs font-medium text-slate-300">Final answer</div>
                                    <label className="flex items-center gap-2 text-xs text-slate-400">
                                        <input type="checkbox" checked={promote} onChange={(e) => setPromote(e.target.checked)} />
                                        Promote to FAQ (optional)
                                    </label>
                                </div>
                                <div className="mt-2">
                                    <Textarea value={finalAnswer} onChange={setFinalAnswer} rows={6} placeholder="Write the official answer…" />
                                </div>
                            </div>

                            <div className="flex gap-2">
                                <Button onClick={resolve} disabled={loading || selected.status !== "open" || !finalAnswer.trim()}>
                                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                                    Resolve
                                </Button>
                                {selected.status === "resolved" && selected.resolvedAt ? (
                                    <Pill tone="ok">Resolved {formatTime(selected.resolvedAt)}</Pill>
                                ) : null}
                            </div>
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
}

// -----------------------------
// Schedule Page
// -----------------------------

function SchedulePage({ api }: { api: any }) {
    const [cfg, setCfg] = useState<ScheduleConfig | null>(null);
    const [raw, setRaw] = useState<string>("");
    const [q, setQ] = useState("What’s my schedule Monday?");
    const [ans, setAns] = useState<string>("");
    const [loading, setLoading] = useState(false);

    async function load() {
        setLoading(true);
        try {
            const s = await api.getSchedule().catch(() => null);
            setCfg(s);
            setRaw(s ? JSON.stringify(s, null, 2) : "");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    async function save() {
        setLoading(true);
        try {
            const parsed = JSON.parse(raw);
            await api.setSchedule(parsed);
            await load();
        } catch (e: any) {
            setAns(`Invalid JSON: ${e?.message ?? ""}`);
        } finally {
            setLoading(false);
        }
    }

    async function ask() {
        setLoading(true);
        try {
            const res = await api.askSchedule(q);
            setAns(res.answer);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
                <CardHeader
                    title="Schedule config"
                    subtitle="Paste JSON (MVP)"
                    right={
                        <Button variant="secondary" onClick={load} disabled={loading}>
                            <RefreshCcw className="h-4 w-4" />
                        </Button>
                    }
                />
                <div className="space-y-3 p-4">
                    <Textarea value={raw} onChange={setRaw} rows={18} />
                    <Button onClick={save} disabled={loading}>
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                        Save schedule
                    </Button>
                    <div className="text-xs text-slate-500">This is separate from policy docs and is treated as a trusted internal source.</div>
                </div>
            </Card>

            <Card className="lg:col-span-2">
                <CardHeader title="Ask Schedule" subtitle={cfg ? `Timezone: ${cfg.timezone}` : "No schedule loaded"} />
                <div className="space-y-4 p-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-end">
                        <div className="flex-1">
                            <div className="mb-1 text-xs text-slate-400">Question</div>
                            <Input value={q} onChange={setQ} />
                        </div>
                        <Button onClick={ask} disabled={loading || !q.trim()}>
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquare className="h-4 w-4" />}
                            Ask
                        </Button>
                    </div>

                    <Card className="border-slate-900 bg-slate-950/40">
                        <div className="p-4">
                            <div className="flex items-center justify-between">
                                <div className="text-xs font-medium text-slate-300">Answer</div>
                                <Pill tone="neutral">Source: schedule config</Pill>
                            </div>
                            <div className="mt-2 text-sm text-slate-100">
                                {ans ? <RichText text={ans} /> : <span className="text-slate-500">Ask a question to see an answer…</span>}
                            </div>
                        </div>
                    </Card>

                    <div>
                        <div className="text-xs font-medium text-slate-300">Weekly view</div>
                        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                            {(cfg?.week ?? []).map((d) => (
                                <Card key={d.day} className="border-slate-900 bg-slate-950/40">
                                    <div className="p-3">
                                        <div className="flex items-center justify-between">
                                            <div className="text-sm font-semibold">{d.day}</div>
                                            <Pill tone="neutral">{d.start}–{d.end}</Pill>
                                        </div>
                                        {d.note ? <div className="mt-2 text-xs text-slate-400">{d.note}</div> : <div className="mt-2 text-xs text-slate-600">—</div>}
                                    </div>
                                </Card>
                            ))}
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
