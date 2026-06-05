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

function movingAverage(values, windowSize = 10) {
  return values.map((_, index) => {
    const start = Math.max(0, index - windowSize + 1);
    const slice = values.slice(start, index + 1);
    return slice.reduce((sum, value) => sum + value, 0) / slice.length;
  });
}

export default function RewardChart({ points = [] }) {
  const rewardValues = points.map((p) => p.value);
  const data = {
    labels: points.map((p) => p.step),
    datasets: [
      {
        label: "Reward",
        data: rewardValues,
        borderColor: "rgba(0, 255, 200, 0.9)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
      },
      {
        label: "10-step moving average",
        data: movingAverage(rewardValues, 10),
        borderColor: "rgba(96, 165, 250, 0.9)",
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [6, 4],
        tension: 0.25,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        display: true,
        labels: { color: "#99f6e4", boxWidth: 10, boxHeight: 10 },
      },
    },
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
    <div className="rounded-xl border border-teal-700/20 bg-black/50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-teal-200">Reward Trend</h4>
        <span className="text-xs text-gray-500">{points.length} points</span>
      </div>
      {points.length > 1 ? (
        <Line data={data} options={options} height={80} />
      ) : (
        <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-teal-500/20 text-sm text-gray-500">
          Start training to plot reward and moving average.
        </div>
      )}
    </div>
  );
}
