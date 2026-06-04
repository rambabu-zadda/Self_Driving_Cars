import React from "react";

export default function TrackView({ src, message = "Waiting for frames..." }) {
  return (
    <div className="w-full h-[500px] bg-black rounded-xl overflow-hidden border border-teal-700/30 flex items-center justify-center">
      {src ? (
        <img
          src={src}
          alt="track"
          className="w-full h-full object-contain transition duration-300"
        />
      ) : (
        <div className="text-center">
          <div className="text-teal-300 opacity-80">{message}</div>
          <div className="mt-2 text-xs text-gray-500">
            Render free instances can take a few seconds before the first training frame appears.
          </div>
        </div>
      )}
    </div>
  );
}
