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
import MetricCard from "./MetricCard";


export default function Dashboard() {
  const [frame, setFrame] = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [currentExperimentId, setCurrentExperimentId] = useState("-");
  const [metrics, setMetrics] = useState({
    episode: "-",
    reward: "-",
    crashes: "-",
    steps: "-",
    epsilon: "-",
    loss: "-",
    qValue: "-",
    replaySize: "-",
    progress: "-",
    action: "-",
    rewardBreakdown: {},
  });

  const [runningState, setRunningState] = useState("stopped"); // running, paused, stopped
  const [controlMode, setControlMode] = useState("local");
  const [controlBusy, setControlBusy] = useState(null);
  const [controlMessage, setControlMessage] = useState("Ready");
  const [connected, setConnected] = useState(false);
  const [connectionMode, setConnectionMode] = useState("Offline");
  const [fps, setFps] = useState(0);
  const [speed, setSpeed] = useState(0);
  const [rewardPoints, setRewardPoints] = useState([]);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const lastDataAtRef = useRef(0);
  const lastFrameAtRef = useRef(0);
  const lastMetricPointRef = useRef("");

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
      if (wsConnected) {
        setConnectionMode("WebSocket");
      } else if (pollingRecentlyWorked) {
        setConnectionMode("Polling");
      } else {
        setConnectionMode("Offline");
      }
    }, 400);

    const pollTelemetry = setInterval(async () => {
      const f = await wsClient.fetchLatestFrame();
      if (f) {
        const now = Date.now();
        if (lastFrameAtRef.current) {
          const refreshFps = 1000 / Math.max(now - lastFrameAtRef.current, 1);
          setFps(Math.max(1, Math.round(refreshFps)));
        }
        lastFrameAtRef.current = now;
        lastDataAtRef.current = Date.now();
        setFrame(f);
      }

      const latestMetric = await wsClient.fetchLatestMetric();
      if (latestMetric) {
        lastDataAtRef.current = Date.now();
        applyMetricSnapshot(latestMetric);
      }
    }, 1500);

    const pollLists = setInterval(() => {
      fetchEpisodes();
      fetchExperiments();
    }, 6000);

    const pollStatus = setInterval(fetchTrainStatus, 2000);

    fetchTrainStatus();
    fetchEpisodes();
    fetchExperiments();

    return () => {
      clearInterval(connCheck);
      clearInterval(pollTelemetry);
      clearInterval(pollLists);
      clearInterval(pollStatus);
      if (wsRef.current) wsRef.current.disconnect();
    };
  }, []); // deliberate empty dependency

  function applyTrainStatus(status) {
    if (!status) return;
    const nextState = status.paused
      ? "paused"
      : status.running
        ? "running"
        : "stopped";
    setRunningState(nextState);
    setControlMode(status.control_mode || "local");
    setCurrentExperimentId(status.experiment_id || "-");
  }

  function formatNumber(value, digits = 2) {
    return typeof value === "number" && Number.isFinite(value)
      ? value.toFixed(digits)
      : value;
  }

  function progressPercent() {
    if (typeof metrics.progress === "number") {
      return Math.max(0, Math.min(100, metrics.progress * 100));
    }
    return 0;
  }

  function stateTone() {
    if (runningState === "running") return "green";
    if (runningState === "paused") return "yellow";
    return "gray";
  }

  function pushRewardPoint(episode, step, value) {
    if (typeof value !== "number" || step == null) return;
    const key = `${episode ?? "unknown"}-${step}`;
    if (lastMetricPointRef.current === key) return;
    lastMetricPointRef.current = key;
    setRewardPoints((prev) => [...prev, { step, value }].slice(-200));
  }

  function applyMetricSnapshot(snapshot) {
    if (!snapshot) return;

    if (snapshot.experiment_id) {
      setCurrentExperimentId(snapshot.experiment_id);
    }

    setMetrics((prev) => ({
      ...prev,
      episode: snapshot.episode ?? prev.episode ?? "-",
      reward:
        typeof snapshot.reward === "number"
          ? snapshot.reward
          : prev.reward ?? "-",
      steps: snapshot.step ?? snapshot.steps ?? prev.steps ?? "-",
      epsilon:
        typeof snapshot.epsilon === "number"
          ? snapshot.epsilon
          : prev.epsilon ?? "-",
      loss:
        typeof snapshot.loss === "number"
          ? snapshot.loss
          : prev.loss ?? "-",
      qValue:
        typeof snapshot.q_value === "number"
          ? snapshot.q_value
          : prev.qValue ?? "-",
      replaySize:
        snapshot.replay_size ?? snapshot.replaySize ?? prev.replaySize ?? "-",
      progress:
        typeof snapshot.progress === "number"
          ? snapshot.progress
          : prev.progress ?? "-",
      rewardBreakdown: snapshot.reward_breakdown ?? prev.rewardBreakdown ?? {},
    }));

    if (typeof snapshot.speed === "number") {
      setSpeed(Number(snapshot.speed || 0).toFixed(2));
    }
    pushRewardPoint(snapshot.episode, snapshot.step ?? snapshot.steps, snapshot.reward);
  }

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
            episode: parsed.metrics.episode ?? "-",
            reward:
              typeof parsed.metrics.reward === "number"
                ? parsed.metrics.reward
                : "-",
            crashes: parsed.metrics.crashes ?? "-",
            steps: parsed.metrics.steps ?? parsed.metrics.step ?? "-",
            epsilon: parsed.metrics.epsilon ?? "-",
            loss: parsed.metrics.loss ?? "-",
            qValue: parsed.metrics.q_value ?? "-",
            replaySize: parsed.metrics.replay_size ?? "-",
            progress: parsed.metrics.progress ?? "-",
            action: parsed.metrics.action ?? "-",
            rewardBreakdown: parsed.metrics.reward_breakdown ?? {},
          });

          if (parsed.metrics.fps) setFps(Math.round(parsed.metrics.fps));
          if (parsed.metrics.speed)
            setSpeed(Number(parsed.metrics.speed || 0).toFixed(2));
          pushRewardPoint(
            parsed.metrics.episode,
            parsed.metrics.steps ?? parsed.metrics.step,
            parsed.metrics.reward
          );
        }
        break;
      }

      case "metric_point":
        pushRewardPoint(parsed.episode, parsed.step, parsed.point);
        break;

      case "episode":
        fetchEpisodes();
        fetchExperiments();
        break;

      case "experiment_start":
        setCurrentExperimentId(parsed.experiment_id || "-");
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
        setControlMessage(`Trainer ${parsed.status || "updated"}`);
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

  async function fetchTrainStatus() {
    try {
      const res = await fetch(`${wsClient.BACKEND}/train/status?t=${Date.now()}`, {
        cache: "no-store",
      });
      if (!res.ok) return null;
      const status = await res.json();
      applyTrainStatus(status);
      return status;
    } catch (e) {
      console.warn("Failed fetch train status", e);
      return null;
    }
  }

  // ------------------------------
  // START / PAUSE / RESET
  // ------------------------------
  async function doAction(action) {
    setControlBusy(action);
    setControlMessage(`${actionLabel(action)} request sent...`);
    setLogs((old) => [
      { ts: Date.now(), msg: `${actionLabel(action)} clicked` },
      ...old.slice(0, 300),
    ]);

    try {
      const res = await fetch(`${wsClient.BACKEND}/train/${action}`, {
        method: "POST",
        cache: "no-store",
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(payload.detail || `HTTP ${res.status}`);
      }

      const changed = Boolean(
        payload.started ?? payload.paused ?? payload.resumed ?? payload.reset
      );
      const message = changed
        ? `${actionLabel(action)} accepted`
        : actionNoopMessage(action, runningState);
      setControlMessage(message);
      setLogs((old) => [
        { ts: Date.now(), msg: `${message} (${payload.control_mode || "local"})` },
        ...old.slice(0, 300),
      ]);

      await fetchTrainStatus();
      if (action === "reset") {
        setFrame(null);
        setRewardPoints([]);
      }
    } catch (e) {
      setControlMessage(`Control failed: ${e.message}`);
      setLogs((old) => [
        { ts: Date.now(), msg: `Control failed: ${e.message}` },
        ...old.slice(0, 300),
      ]);
    } finally {
      setControlBusy(null);
    }
  }

  function actionLabel(action) {
    return action.charAt(0).toUpperCase() + action.slice(1);
  }

  function actionNoopMessage(action, state) {
    if (action === "start" && state === "running") return "Trainer is already running";
    if (action === "pause" && state !== "running") return "Trainer is not running";
    if (action === "resume" && state !== "paused") return "Trainer is not paused";
    if (action === "reset" && state === "stopped") return "Trainer is already stopped";
    return `${actionLabel(action)} did not change trainer state`;
  }

  function trackMessage() {
    if (runningState === "running") return "Trainer is running. Waiting for first frame...";
    if (runningState === "paused") return "Training paused.";
    return "Click Start to begin training.";
  }

  function buttonClass(kind, active = false) {
    const base =
      "rounded-xl px-4 py-3 font-semibold transition disabled:cursor-not-allowed disabled:opacity-50";
    if (kind === "start") {
      return `${base} ${
        active
          ? "bg-gradient-to-r from-green-300 to-teal-300 text-black shadow-lg shadow-green-500/20"
          : "bg-gradient-to-r from-teal-500 to-cyan-500 text-black hover:scale-[1.02]"
      }`;
    }
    if (kind === "pause") return `${base} bg-slate-800 text-gray-100 hover:bg-slate-700`;
    if (kind === "resume") return `${base} bg-blue-600/80 text-white hover:bg-blue-500`;
    return `${base} bg-red-600 text-white hover:bg-red-500`;
  }

  // ------------------------------
  // RENDER UI
  // ------------------------------
  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(45,212,191,0.18),_transparent_35%),linear-gradient(180deg,#0f172a,#020617_55%,#000)] p-4 text-white md:p-6">
      {/* HEADER */}
      <div className="mb-6 rounded-3xl border border-white/10 bg-white/[0.04] p-5 shadow-2xl shadow-black/30 backdrop-blur">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="mb-2 inline-flex rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-teal-200">
              Reinforcement Learning Lab
            </div>
            <h1 className="text-3xl font-black tracking-tight text-white md:text-5xl">
              Autonomous Driving RL Simulation
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-gray-400 md:text-base">
              Train, monitor, and evaluate a DQN driving agent with live frames, reward telemetry, and deployment-safe polling.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <WSIndicator connected={connected} mode={connectionMode} />
            <FPSCounter fps={fps} />
            <button
              onClick={() => doAction("start")}
              disabled={Boolean(controlBusy)}
              className={buttonClass("start", runningState === "running")}
            >
              {controlBusy === "start" ? "Starting..." : "Start Training"}
            </button>

            <button
              onClick={() => doAction("reset")}
              disabled={Boolean(controlBusy)}
              className={buttonClass("reset")}
            >
              {controlBusy === "reset" ? "Resetting..." : "Reset"}
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-5">
          <MetricCard title="Trainer" value={runningState} subtitle={controlMessage} tone={stateTone()} small />
          <MetricCard title="Episode" value={metrics.episode} subtitle="Current run" tone="teal" small />
          <MetricCard title="Reward" value={formatNumber(metrics.reward, 2)} subtitle="Total return" tone="green" small />
          <MetricCard title="Steps" value={metrics.steps} subtitle="Episode step" tone="blue" small />
          <MetricCard title="Epsilon" value={formatNumber(metrics.epsilon, 3)} subtitle="Exploration" tone="yellow" small />
        </div>
      </div>

      {/* BODY GRID */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* LEFT SIDE */}
        <div className="xl:col-span-2 rounded-3xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-gray-950/90 p-4 shadow-2xl shadow-black/30">
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-teal-200">
                Virtual Track Environment
              </h2>
              <p className="text-sm text-gray-500">
                Live visual feed from the deployed trainer. First frame may take a short warmup.
              </p>
            </div>
            <div className="min-w-[220px]">
              <div className="flex justify-between text-xs text-gray-400">
                <span>Route Progress</span>
                <strong className="text-teal-200">{progressPercent().toFixed(1)}%</strong>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-teal-400 to-cyan-300 transition-all duration-500"
                  style={{ width: `${progressPercent()}%` }}
                />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-teal-400/10 bg-black/70 p-3 shadow-inner shadow-teal-500/5">
            <TrackView src={frame} message={trackMessage()} />
          </div>

          {/* METRICS ROW */}
          <div className="mt-4 flex flex-col items-stretch gap-4 lg:flex-row lg:items-center">
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
        <div className="rounded-3xl border border-white/10 bg-zinc-950/90 p-4 shadow-2xl shadow-black/30">
          <h3 className="mb-2 text-xl font-bold text-teal-200">Training Controls</h3>

          <div className="grid gap-3">
            <div className="rounded-2xl bg-black/30 p-4 ring-1 ring-white/10">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-gray-400">Trainer Status</span>
                <strong
                  className={`capitalize ${
                    runningState === "running"
                      ? "text-green-300"
                      : runningState === "paused"
                        ? "text-yellow-200"
                        : "text-gray-300"
                  }`}
                >
                  {runningState}
                </strong>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3 text-xs text-gray-500">
                <span>Mode: {controlMode}</span>
                <span>{controlMessage}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => doAction("start")}
                disabled={Boolean(controlBusy)}
                className={buttonClass("start", runningState === "running")}
              >
                {controlBusy === "start" ? "Starting..." : "Start"}
              </button>
              <button
                onClick={() => doAction("pause")}
                disabled={Boolean(controlBusy)}
                className={buttonClass("pause")}
              >
                {controlBusy === "pause" ? "Pausing..." : "Pause"}
              </button>
              <button
                onClick={() => doAction("resume")}
                disabled={Boolean(controlBusy)}
                className={buttonClass("resume")}
              >
                {controlBusy === "resume" ? "Resuming..." : "Resume"}
              </button>
              <button
                onClick={() => doAction("reset")}
                disabled={Boolean(controlBusy)}
                className={buttonClass("reset")}
              >
                {controlBusy === "reset" ? "Resetting..." : "Reset"}
              </button>
            </div>

            {/* METRICS */}
            <div className="mt-2">
              <h4 className="text-sm text-teal-200">Latest Metrics</h4>
              <div className="mt-2 grid grid-cols-1 gap-2">
                <div className="break-all rounded-xl bg-gray-900/80 p-3">
                  Experiment: <strong>{currentExperimentId}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Episode: <strong>{metrics.episode}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Reward:{" "}
                  <strong>
                    {formatNumber(metrics.reward, 2)}
                  </strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Crashes: <strong>{metrics.crashes}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Steps: <strong>{metrics.steps}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Epsilon: <strong>{formatNumber(metrics.epsilon, 3)}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Loss: <strong>{formatNumber(metrics.loss, 4)}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Q Value: <strong>{formatNumber(metrics.qValue, 4)}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
                  Replay Buffer: <strong>{metrics.replaySize}</strong>
                </div>
                <div className="rounded-xl bg-gray-900/80 p-3">
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
                            : "-"}
                        </strong>
                      </span>
                      <span>
                        Collision:{" "}
                        <strong>
                          {typeof experiment.collision_rate === "number"
                            ? `${(experiment.collision_rate * 100).toFixed(1)}%`
                            : "-"}
                        </strong>
                      </span>
                      <span>
                        Success:{" "}
                        <strong>
                          {typeof experiment.success_rate === "number"
                            ? `${(experiment.success_rate * 100).toFixed(1)}%`
                            : "-"}
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
