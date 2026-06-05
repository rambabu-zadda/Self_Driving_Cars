import React from "react";

export default function TrackView({ src, message = "Waiting for frames..." }) {
  return (
    <div className="relative flex h-[500px] w-full items-center justify-center overflow-hidden rounded-2xl border border-teal-700/30 bg-black">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(45,212,191,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(45,212,191,0.05)_1px,transparent_1px)] bg-[size:28px_28px]" />
      <div className="pointer-events-none absolute left-4 top-4 z-10 rounded-full border border-teal-300/20 bg-black/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200">
        Live Track Feed
      </div>
      {src ? (
        <img
          src={src}
          alt="track"
          className="relative z-0 h-full w-full object-contain transition duration-300"
        />
      ) : (
        <div className="relative z-10 max-w-md px-6 text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-pulse rounded-full border border-teal-300/30 bg-teal-300/10 shadow-lg shadow-teal-400/20" />
          <div className="text-lg font-semibold text-teal-200">{message}</div>
          <div className="mt-2 text-xs text-gray-500">
            Render free instances can take a few seconds before the first training frame appears.
          </div>
        </div>
      )}
    </div>
  );
}
