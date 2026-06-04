// frontend/src/components/WSIndicator.jsx
import React from "react";

export default function WSIndicator({ connected }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${connected ? "bg-green-400 shadow-lg" : "bg-red-600"}`} />
      <div className="text-sm text-gray-300">{connected ? "Connected" : "Disconnected"}</div>
    </div>
  );
}
