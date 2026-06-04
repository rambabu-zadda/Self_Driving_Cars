import React from "react";

export default function TrackView({ src }) {
  return (
    <div className="w-full h-[500px] bg-black rounded-xl overflow-hidden border border-teal-700/30 flex items-center justify-center">
      {src ? (
        <img
          src={src}
          alt="track"
          className="w-full h-full object-contain transition duration-300"
        />
      ) : (
        <div className="text-teal-300 opacity-60">Waiting for frames...</div>
      )}
    </div>
  );
}
