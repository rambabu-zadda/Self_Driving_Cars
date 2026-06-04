import React from "react";
import { Line } from "react-chartjs-2";

export default function EpisodeSummary({ episodes = [] }) {
  const rewardData = {
    labels: episodes.map(e => `Ep ${e.episode}`),
    datasets: [{
      label: "Total Reward",
      data: episodes.map(e => e.reward),
      borderColor: "rgb(0,255,200)",
      borderWidth: 2,
      tension: 0.2
    }]
  };

  const stepsData = {
    labels: episodes.map(e => `Ep ${e.episode}`),
    datasets: [{
      label: "Steps",
      data: episodes.map(e => e.duration),
      borderColor: "rgb(0,150,255)",
      borderWidth: 2,
      tension: 0.2
    }]
  };

  const crashData = {
    labels: episodes.map(e => `Ep ${e.episode}`),
    datasets: [{
      label: "Crashes",
      data: episodes.map(e => e.crashes),
      borderColor: "rgb(255,80,80)",
      borderWidth: 2,
      tension: 0.2
    }]
  };

  const options = {
    responsive: true,
    plugins: { legend: { labels: { color: "#44f6d2" } } },
    scales: {
      x: { ticks: { color: "#55f6ce" } },
      y: { ticks: { color: "#55f6ce" } }
    }
  };

  return (
    <div className="space-y-6 bg-black/40 p-4 rounded-xl border border-teal-600/20">
      <h3 className="text-teal-300 text-xl font-semibold mb-4">Episode Summary</h3>

      <div>
        <h4 className="text-teal-200 mb-2">Reward per Episode</h4>
        <Line data={rewardData} options={options} height={80} />
      </div>

      <div>
        <h4 className="text-teal-200 mb-2">Steps per Episode</h4>
        <Line data={stepsData} options={options} height={80} />
      </div>

      <div>
        <h4 className="text-teal-200 mb-2">Crashes per Episode</h4>
        <Line data={crashData} options={options} height={80} />
      </div>
    </div>
  );
}
