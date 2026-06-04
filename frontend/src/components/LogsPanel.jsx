// frontend/src/components/LogsPanel.jsx
import React, { useRef, useEffect } from "react";

export default function LogsPanel({ logs = [] }) {
  const box = useRef(null);
  useEffect(() => {
    if (box.current) box.current.scrollTop = 0;
  }, [logs]);

  return (
    <div ref={box} className="h-40 overflow-auto bg-black/20 rounded p-2 text-xs">
      {logs.length === 0 && <div className="text-gray-500">No logs yet</div>}
      {logs.map((l, idx) => (
        <div key={idx} className="text-gray-300">
          <span className="text-gray-500 mr-2">[{new Date(l.ts).toLocaleTimeString()}]</span>
          {l.msg}
        </div>
      ))}
    </div>
  );
}

