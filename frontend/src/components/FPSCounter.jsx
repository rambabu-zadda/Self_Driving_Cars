// frontend/src/components/FPSCounter.jsx
import React from "react";

export default function FPSCounter({ fps }) {
  return (
    <div className="px-3 py-1 rounded bg-black/40 text-sm">
      <div className="text-xs text-gray-400">FPS</div>
      <div className="text-lg font-semibold text-teal-300">{fps}</div>
    </div>
  );
}
