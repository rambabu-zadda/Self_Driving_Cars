import React from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
} from "chart.js";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement);

export default function RewardChart({ points = [] }) {
  const data = {
    labels: points.map((p) => p.step),
    datasets: [
      {
        label: "Reward",
        data: points.map((p) => p.value),
        borderColor: "rgba(0, 255, 200, 0.9)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        grid: { color: "rgba(0,255,200,0.05)" },
        ticks: { color: "#55f6ce" },
      },
      y: {
        grid: { color: "rgba(0,255,200,0.05)" },
        ticks: { color: "#55f6ce" },
      },
    },
  };

  return (
    <div className="bg-black/50 p-3 rounded-xl border border-teal-700/20">
      <Line data={data} options={options} height={80} />
    </div>
  );
}
