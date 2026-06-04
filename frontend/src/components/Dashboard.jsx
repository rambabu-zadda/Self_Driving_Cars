// frontend/src/components/Dashboard.jsx
import React, { useEffect, useRef, useState } from "react";
import wsClient from "../api/wsClient";
import TrackView from "./TrackView";
import Gauge from "./Gauge";
import WSIndicator from "./WSIndicator";
import FPSCounter from "./FPSCounter";
import Speedometer from "./Speedometer";
import RewardChart from "./RewardChart";
import LogsPanel from "./LogsPanel";
import ErrorPopup from "./ErrorPopup";
import EpisodeSummary from "./EpisodeSummary";


export default function Dashboard() {
  const [frame, setFrame] = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [currentExperimentId, setCurrentExperimentId] = useState("—");
  const [metrics, setMetrics] = useState({
    episode: "—",
    reward: "—",
    crashes: "—",
    steps: "—",
    epsilon: "—",
    loss: "—",
    replaySize: "—",
    action: "—",
    rewardBreakdown: {},
  });

  const [runningState, setRunningState] = useState("stopped"); // running, paused, stopped
  const [connected, setConnected] = useState(false);
  const [fps, setFps] = useState(0);
  const [speed, setSpeed] = useState(0);
  const [rewardPoints, setRewardPoints] = useState([]);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const lastDataAtRef = useRef(0);

  // ------------------------------
  // INITIALIZATION + WS CONNECTION
  // ------------------------------
  useEffect(() => {
    wsRef.current = wsClient.connect((msg) => {
      try {
        const parsed = JSON.parse(msg.text);
        lastDataAtRef.current = Date.now();
        handleMessage(parsed);
      } catch {
        console.log("WS raw:", msg.text);
      }
    });

    const connCheck = setInterval(() => {
      const wsConnected = wsRef.current && wsRef.current.readyState === 1;
      const pollingRecentlyWorked = Date.now() - lastDataAtRef.current < 5000;
      setConnected(Boolean(wsConnected || pollingRecentlyWorked));
    }, 400);

    const pollFrame = setInterval(async () => {
      const f = await wsClient.fetchLatestFrame();
      if (f) {
        lastDataAtRef.current = Date.now();
        setFrame(f);
      }
    }, 1500);

    fetchEpisodes();
    fetchExperiments();

    return () => {
      clearInterval(connCheck);
      clearInterval(pollFrame);
      if (wsRef.current) wsRef.current.disconnect();
    };
  }, []); // deliberate empty dependency

  // ------------------------------
  // HANDLE WS MESSAGES
  // ------------------------------
  function handleMessage(parsed) {
    if (!parsed || !parsed.type) return;

    switch (parsed.type) {
      case "frame": {
        if (parsed.experiment_id) setCurrentExperimentId(parsed.experiment_id);
        if (parsed.png_b64) {
          setFrame("data:image/png;base64," + parsed.png_b64);
        }
        if (parsed.metrics) {
          setMetrics({
            episode: parsed.metrics.episode ?? "—",
            reward:
              typeof parsed.metrics.reward === "number"
                ? parsed.metrics.reward
                : "—",
            crashes: parsed.metrics.crashes ?? "—",
            steps: parsed.metrics.steps ?? "—",
            epsilon: parsed.metrics.epsilon ?? "—",
            loss: parsed.metrics.loss ?? "—",
            replaySize: parsed.metrics.replay_size ?? "—",
            action: parsed.metrics.action ?? "—",
            rewardBreakdown: parsed.metrics.reward_breakdown ?? {},
          });

          if (parsed.metrics.fps) setFps(Math.round(parsed.metrics.fps));
          if (parsed.metrics.speed)
            setSpeed(Number(parsed.metrics.speed || 0).toFixed(2));
        }
        break;
      }

      case "metric_point":
        setRewardPoints((prev) => {
          const next = [...prev, { step: parsed.step, value: parsed.point }];
          return next.slice(-200);
        });
        break;

      case "episode":
        fetchEpisodes();
        fetchExperiments();
        break;

      case "experiment_start":
        setCurrentExperimentId(parsed.experiment_id || "—");
        fetchExperiments();
        break;

      case "experiment_end":
      case "checkpoint":
        fetchExperiments();
        break;

      case "log":
        setLogs((old) => [
          { ts: Date.now(), msg: parsed.message },
          ...old.slice(0, 300),
        ]);
        break;

      case "status":
        if (parsed.experiment_id) setCurrentExperimentId(parsed.experiment_id);
        setRunningState(parsed.status || runningState);
        setLogs((old) => [
          { ts: Date.now(), msg: `Status: ${parsed.status}` },
          ...old.slice(0, 300),
        ]);
        break;

      case "error":
        setError(parsed.message || "Unknown error");
        setLogs((old) => [
          { ts: Date.now(), msg: `ERROR: ${parsed.message}` },
          ...old.slice(0, 300),
        ]);
        break;

      default:
        break;
    }
  }

  // ------------------------------
  // FETCH EPISODES
  // ------------------------------
  async function fetchEpisodes() {
    try {
      const res = await fetch(`${wsClient.BACKEND}/episodes?limit=5&t=${Date.now()}`, {
        cache: "no-store",
      });
      if (!res.ok) return;
      const arr = await res.json();
      setEpisodes(arr);
    } catch (e) {
      console.warn("Failed fetch episodes", e);
    }
  }

  async function fetchExperiments() {
    try {
      const res = await fetch(`${wsClient.BACKEND}/experiments?limit=5&t=${Date.now()}`, {
        cache: "no-store",
      });
      if (!res.ok) return;
      const arr = await res.json();
      setExperiments(arr);
    } catch (e) {
      console.warn("Failed fetch experiments", e);
    }
  }

  // ------------------------------
  // START / PAUSE / RESET
  // ------------------------------
  async function doAction(action) {
    try {
      await fetch(`${wsClient.BACKEND}/train/${action}`, { method: "POST" });
    } catch (e) {
      setLogs((old) => [
        { ts: Date.now(), msg: `Control failed: ${e.message}` },
        ...old.slice(0, 300),
      ]);
    }
  }

  // ------------------------------
  // RENDER UI
  // ------------------------------
  return (
    <div className="min-h-screen p-6 bg-gradient-to-b from-gray-900 to-black text-white">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-teal-300">
          Autonomous Driving RL Simulation
        </h1>

        <div className="flex items-center gap-4">
          <WSIndicator connected={connected} />
          <FPSCounter fps={fps} />
          <div className="space-x-2">
            <button
              onClick={() => doAction("start")}
              className={`px-4 py-2 rounded-lg font-semibold shadow-lg transition ${
                runningState === "running"
                  ? "bg-gradient-to-r from-green-400 to-teal-300 text-black ring-4 ring-green-400/30"
                  : "bg-gradient-to-r from-teal-600 to-cyan-500"
              }`}
            >
              ▶ Start Training
            </button>

            <button
              onClick={() => doAction("reset")}
              className="px-3 py-2 border border-teal-700 rounded-md hover:bg-teal-900"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {/* BODY GRID */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* LEFT SIDE */}
        <div className="xl:col-span-2 bg-gradient-to-b from-zinc-900 to-gray-900 rounded-xl p-4 ring-1 ring-teal-900/20">
          <h2 className="text-xl text-teal-300 mb-3">
            Virtual Track Environment
          </h2>

          <div className="rounded-lg border border-teal-800/20 p-3 bg-black">
            <TrackView src={frame} />
          </div>

          {/* METRICS ROW */}
          <div className="mt-4 flex flex-col lg:flex-row items-stretch lg:items-center gap-4">
            <Speedometer speed={speed} />

            <div className="flex-1">
              <RewardChart points={rewardPoints} />
            </div>

            <div className="w-40">
              <Gauge title="Episode" value={metrics.episode} />
              <Gauge
                title="Reward"
                value={
                  typeof metrics.reward === "number"
                    ? metrics.reward.toFixed(2)
                    : metrics.reward
                }
              />
            </div>
          </div>
        </div>

        {/* RIGHT SIDE */}
        <div className="bg-zinc-900 rounded-xl p-4 ring-1 ring-teal-900/20">
          <h3 className="text-lg text-teal-300 mb-2">Training Controls</h3>

          <div className="grid gap-3">
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => doAction("start")}
                className="px-3 py-2 rounded bg-gradient-to-r from-green-400 to-teal-300 text-black"
              >
                Start
              </button>
              <button
                onClick={() => doAction("pause")}
                className="px-3 py-2 rounded bg-gray-800"
              >
                Pause
              </button>
              <button
                onClick={() => doAction("resume")}
                className="px-3 py-2 rounded bg-gray-800"
              >
                Resume
              </button>
              <button
                onClick={() => doAction("reset")}
                className="px-3 py-2 rounded bg-red-600"
              >
                Reset
              </button>
            </div>

            {/* METRICS */}
            <div className="mt-2">
              <h4 className="text-sm text-teal-200">Latest Metrics</h4>
              <div className="grid grid-cols-1 gap-2 mt-2">
                <div className="p-2 bg-gray-900 rounded break-all">
                  Experiment: <strong>{currentExperimentId}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Episode: <strong>{metrics.episode}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Reward:{" "}
                  <strong>
                    {typeof metrics.reward === "number"
                      ? metrics.reward.toFixed(2)
                      : metrics.reward}
                  </strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Crashes: <strong>{metrics.crashes}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Steps: <strong>{metrics.steps}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Epsilon: <strong>{typeof metrics.epsilon === "number" ? metrics.epsilon.toFixed(3) : metrics.epsilon}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Loss: <strong>{typeof metrics.loss === "number" ? metrics.loss.toFixed(4) : metrics.loss}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Replay Buffer: <strong>{metrics.replaySize}</strong>
                </div>
                <div className="p-2 bg-gray-900 rounded">
                  Last Action: <strong>{metrics.action}</strong>
                </div>
              </div>
            </div>

            <div className="mt-2">
              <h4 className="text-sm text-teal-200">Reward Breakdown</h4>
              <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                {Object.entries(metrics.rewardBreakdown).map(([name, value]) => (
                  <div key={name} className="p-2 bg-gray-900 rounded flex justify-between">
                    <span className="capitalize text-gray-400">{name.replace("_", " ")}</span>
                    <strong>{Number(value).toFixed(2)}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* LOG PANEL */}
            <div className="mt-4">
              <h4 className="text-sm text-teal-200 mb-2">Training Logs</h4>
              <LogsPanel logs={logs} />
            </div>
            <div className="mt-6">
              <EpisodeSummary episodes={episodes} />
            </div>
            <div className="mt-6">
              <h4 className="text-sm text-teal-200 mb-2">Experiment Explorer</h4>
              <div className="space-y-2">
                {experiments.length === 0 && (
                  <div className="text-gray-500 text-sm bg-black/20 rounded p-3">
                    No experiments recorded yet.
                  </div>
                )}
                {experiments.map((experiment) => (
                  <div key={experiment.id} className="bg-black/30 rounded p-3 text-sm">
                    <div className="flex justify-between gap-3">
                      <strong className="text-teal-200 break-all">{experiment.id}</strong>
                      <span className="text-xs text-gray-400">{experiment.status}</span>
                    </div>
                    <div className="text-gray-400">{experiment.algorithm}</div>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <span>Episodes: <strong>{experiment.episode_count}</strong></span>
                      <span>
                        Avg Reward:{" "}
                        <strong>
                          {typeof experiment.average_reward === "number"
                            ? experiment.average_reward.toFixed(2)
                            : "—"}
                        </strong>
                      </span>
                      <span>
                        Collision:{" "}
                        <strong>
                          {typeof experiment.collision_rate === "number"
                            ? `${(experiment.collision_rate * 100).toFixed(1)}%`
                            : "—"}
                        </strong>
                      </span>
                      <span>
                        Success:{" "}
                        <strong>
                          {typeof experiment.success_rate === "number"
                            ? `${(experiment.success_rate * 100).toFixed(1)}%`
                            : "—"}
                        </strong>
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <ErrorPopup error={error} onClose={() => setError(null)} />
    </div>
  );
}
