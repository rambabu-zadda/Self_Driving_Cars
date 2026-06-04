// frontend/src/components/ErrorPopup.jsx
import React from "react";

export default function ErrorPopup({ error, onClose }) {
  if (!error) return null;
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="bg-zinc-900 border border-red-700 rounded p-6 z-60 w-96 shadow-lg">
        <h3 className="text-lg text-red-400 mb-2">An error occurred</h3>
        <div className="text-sm text-gray-300 mb-4">{error}</div>
        <div className="text-right">
          <button onClick={onClose} className="px-3 py-1 bg-red-600 rounded">Close</button>
        </div>
      </div>
    </div>
  );
}
