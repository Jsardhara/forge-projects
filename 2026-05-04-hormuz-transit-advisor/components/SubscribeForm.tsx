"use client";

import { useState } from "react";

type Status = "idle" | "submitting" | "ok" | "error";

export function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string>("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("submitting");
    setMessage("");
    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus("error");
        setMessage(data?.error ?? "Subscription failed.");
        return;
      }
      setStatus("ok");
      setMessage("You are on the list.");
      setEmail("");
    } catch {
      setStatus("error");
      setMessage("Network error. Try again.");
    }
  }

  return (
    <section
      aria-labelledby="subscribe-heading"
      className="relative rounded-3xl bg-gradient-to-br from-ink-800 to-ink-900 ring-1 ring-white/5 shadow-panel p-6 md:p-8 overflow-hidden"
    >
      <div
        aria-hidden
        className="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-bone-200/5 blur-3xl"
      />
      <div className="relative">
        <h2
          id="subscribe-heading"
          className="font-mono uppercase tracking-[0.25em] text-xs text-bone-200/70"
        >
          Brief me when status changes
        </h2>
        <p className="mt-2 text-sm text-bone-200/70 max-w-md leading-relaxed">
          One email per level transition (Green → Amber → Red → Black). No marketing.
          Logged to a local file for now; SendGrid wiring is a flag flip away.
        </p>

        <form onSubmit={onSubmit} className="mt-5 flex flex-col sm:flex-row gap-3">
          <label htmlFor="email" className="sr-only">
            Email address
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            placeholder="captain@operator.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="flex-1 rounded-xl bg-ink-950 border border-white/10 px-4 py-3 text-bone-50 placeholder:text-bone-200/30 focus:outline-none focus:ring-2 focus:ring-bone-200/30 focus:border-bone-200/40"
          />
          <button
            type="submit"
            disabled={status === "submitting"}
            className="rounded-xl bg-bone-50 text-ink-950 px-5 py-3 font-medium hover:bg-bone-100 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {status === "submitting" ? "Sending…" : "Subscribe"}
          </button>
        </form>

        {message && (
          <p
            role="status"
            className={`mt-3 text-sm ${status === "ok" ? "text-emerald-400" : "text-risk-red"}`}
          >
            {message}
          </p>
        )}
      </div>
    </section>
  );
}
