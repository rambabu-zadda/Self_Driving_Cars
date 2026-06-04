// frontend/src/components/WSIndicator.jsx
import React from "react";

export default function WSIndicator({ connected, mode = connected ? "WebSocket" : "Offline" }) {
  const isWebSocket = mode === "WebSocket";
  const isPolling = mode === "Polling";
  const dotClass = isWebSocket
    ? "bg-green-400 shadow-lg shadow-green-400/30"
    : isPolling
      ? "bg-yellow-300 shadow-lg shadow-yellow-300/30"
      : "bg-red-600";
  const textClass = isWebSocket
    ? "text-green-200"
    : isPolling
      ? "text-yellow-100"
      : "text-gray-300";

  return (
    <div className="flex items-center gap-2 rounded-full bg-black/30 px-3 py-2 ring-1 ring-white/10">
      <div className={`h-3 w-3 rounded-full ${dotClass}`} />
      <div className="leading-tight">
        <div className="text-[10px] uppercase tracking-widest text-gray-500">Data Link</div>
        <div className={`text-sm font-semibold ${textClass}`}>{mode}</div>
      </div>
    </div>
  );
}
