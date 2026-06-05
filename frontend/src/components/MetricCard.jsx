import React from "react";

export default function MetricCard({ title, value, subtitle, tone = "teal", small }) {
  const tones = {
    teal: "from-teal-500/20 to-cyan-500/10 border-teal-400/20 text-teal-200",
    green: "from-green-500/20 to-emerald-500/10 border-green-400/20 text-green-200",
    yellow: "from-yellow-500/20 to-orange-500/10 border-yellow-400/20 text-yellow-100",
    red: "from-red-500/20 to-rose-500/10 border-red-400/20 text-red-100",
    blue: "from-blue-500/20 to-indigo-500/10 border-blue-400/20 text-blue-100",
    gray: "from-slate-500/20 to-zinc-500/10 border-white/10 text-gray-100",
  };

  return (
    <div className={`rounded-2xl border bg-gradient-to-br p-4 shadow-lg shadow-black/20 ${tones[tone] || tones.teal}`}>
      <div className="text-xs uppercase tracking-[0.2em] text-gray-400">{title}</div>
      <div className={`mt-2 font-bold ${small ? "text-xl" : "text-3xl"}`}>{value}</div>
      {subtitle && <div className="mt-1 text-xs text-gray-500">{subtitle}</div>}
    </div>
  );
}
