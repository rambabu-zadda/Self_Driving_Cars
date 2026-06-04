import React from "react";

export default function Speedometer({ speed = 0 }) {
  const val = Number(speed) || 0;
  const pct = Math.min(100, (val / 20) * 100); // smooth scaling

  return (
    <div className="bg-black/40 p-4 rounded-xl border border-teal-700/20 w-40">
      <h4 className="text-teal-300 text-sm mb-1">Speed</h4>
      <div className="text-3xl font-bold text-teal-200 mb-1">{val} m/s</div>

      <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          style={{ width: `${pct}%` }}
          className="h-full bg-gradient-to-r from-teal-400 to-cyan-300 transition-all"
        />
      </div>
    </div>
  );
}
