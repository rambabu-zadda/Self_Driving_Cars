// frontend/src/components/Gauge.jsx
import React from "react";

export default function Gauge({ title, value }) {
  return (
    <div className="p-2 bg-black/40 rounded-md border border-teal-800/30">
      <div className="text-xs text-gray-400">{title}</div>
      <div className="text-xl font-semibold text-teal-300">{value}</div>
    </div>
  );
}
