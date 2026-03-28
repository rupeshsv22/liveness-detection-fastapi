import { useRef, useState, useEffect, useCallback } from "react";
import ChallengeList from "./components/ChallengeList.jsx";
import ScoreGauge from "./components/ScoreGauge.jsx";
import StatusBadge from "./components/StatusBadge.jsx";

const API = "";          // proxied via vite — empty = same origin
const FPS = 12;          // frames per second to send
const JPEG_QUALITY = 0.7;

// ── helpers ──────────────────────────────────────────────────────────────────
function frameToBase64(video, canvas, quality = JPEG_QUALITY) {
  const ctx = canvas.getContext("2d");
  canvas.width = 640;
  canvas.height = 480;
  ctx.drawImage(video, 0, 0, 640, 480);
  const dataUrl = canvas.toDataURL("image/jpeg", quality);
  return dataUrl.split(",")[1]; // strip data:image/jpeg;base64,
}

// ── main component ────────────────────────────────────────────────────────────
export default function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const intervalRef = useRef(null);
  const streamRef = useRef(null);

  const [phase, setPhase] = useState("idle"); // idle | starting | streaming | done | result
  const [sessionId, setSessionId] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [sessionStatus, setSessionStatus] = useState("PENDING");
  const [completedCount, setCompletedCount] = useState(0);
  const [currentChallengeIndex, setCurrentChallengeIndex] = useState(0);
  const [frameData, setFrameData] = useState(null);   // latest WS frame response
  const [result, setResult] = useState(null);         // final result
  const [error, setError] = useState(null);
  const [log, setLog] = useState([]);
  const [userId, setUserId] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(null);

  // ── elapsed timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    let t;
    if (phase === "streaming") {
      startTimeRef.current = Date.now();
      t = setInterval(() => setElapsed(((Date.now() - startTimeRef.current) / 1000).toFixed(1)), 100);
    } else {
      setElapsed(0);
    }
    return () => clearInterval(t);
  }, [phase]);

  const addLog = useCallback((msg, type = "info") => {
    setLog(prev => [{msg, type, ts: new Date().toLocaleTimeString()}, ...prev].slice(0, 60));
  }, []);

  // ── cleanup ────────────────────────────────────────────────────────────────
  const cleanup = useCallback(() => {
    clearInterval(intervalRef.current);
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); streamRef.current = null; }
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  // ── start session ──────────────────────────────────────────────────────────
  const startSession = useCallback(async () => {
    setError(null);
    setResult(null);
    setFrameData(null);
    setLog([]);
    setPhase("starting");

    try {
      // 1. Start session
      const res = await fetch(`${API}/api/liveness/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId || undefined }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const session = await res.json();

      setSessionId(session.session_id);
      setChallenges(session.challenges);
      setSessionStatus("IN_PROGRESS");
      setCompletedCount(0);
      setCurrentChallengeIndex(0);
      addLog(`Session created: ${session.session_id.slice(0, 8)}…`, "info");
      addLog(`${session.challenges.length} challenges assigned`, "info");

      // 2. Webcam
      const camStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      streamRef.current = camStream;
      videoRef.current.srcObject = camStream;
      await videoRef.current.play();

      // 3. WebSocket
      const wsUrl = `ws://${window.location.host}/api/liveness/stream/${session.session_id}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        addLog("WebSocket connected", "info");
        setPhase("streaming");

        // Start sending frames
        intervalRef.current = setInterval(() => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const frame = frameToBase64(videoRef.current, canvasRef.current);
          ws.send(JSON.stringify({ frame, timestamp: Date.now() }));
        }, Math.floor(1000 / FPS));
      };

      ws.onmessage = (evt) => {
        let data;
        try { data = JSON.parse(evt.data); } catch { return; }

        // Completion
        if (data.session_complete) {
          clearInterval(intervalRef.current);
          setResult({ liveness_score: data.liveness_score, passed: data.passed });
          setSessionStatus(data.passed ? "COMPLETED" : "FAILED");
          setPhase("done");
          addLog(`Session complete — score: ${data.liveness_score} | ${data.passed ? "PASSED ✓" : "FAILED ✗"}`, data.passed ? "success" : "error");
          ws.close();
          return;
        }

        // Error from server
        if (data.error) {
          addLog(`Server: ${data.error}`, "error");
          if (data.session_complete === false || data.liveness_score !== undefined) {
            setPhase("done");
          }
        }

        setFrameData(data);

        if (data.challenge_completed) {
          setCompletedCount(prev => {
            const next = prev + 1;
            setCurrentChallengeIndex(next);
            return next;
          });
          addLog(`Challenge ${data.current_challenge?.type} completed!`, "success");
        }

        if (data.spoof_detected) addLog("Spoof detected!", "error");
      };

      ws.onerror = () => { addLog("WebSocket error", "error"); setError("WebSocket error"); };
      ws.onclose = (e) => {
        addLog(`WebSocket closed (${e.code})`, "info");
        clearInterval(intervalRef.current);
      };

    } catch (err) {
      setError(err.message);
      setPhase("idle");
      addLog(`Error: ${err.message}`, "error");
    }
  }, [userId, addLog]);

  const reset = useCallback(() => {
    cleanup();
    setPhase("idle");
    setSessionId(null);
    setChallenges([]);
    setSessionStatus("PENDING");
    setCompletedCount(0);
    setCurrentChallengeIndex(0);
    setFrameData(null);
    setResult(null);
    setError(null);
    setLog([]);
  }, [cleanup]);

  // ── fetch final result from REST ──────────────────────────────────────────
  const fetchResult = useCallback(async () => {
    if (!sessionId) return;
    try {
      const res = await fetch(`${API}/api/liveness/result/${sessionId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
      addLog("Result fetched from REST endpoint", "info");
    } catch (err) {
      addLog(`REST fetch error: ${err.message}`, "error");
    }
  }, [sessionId, addLog]);

  // ── derived ────────────────────────────────────────────────────────────────
  const isStreaming = phase === "streaming";
  const isDone = phase === "done";
  const currentChallenge = challenges[currentChallengeIndex];

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "#0f1117", color: "#e2e8f0", padding: "24px 16px" }}>
      {/* Header */}
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9" }}>
              Face Liveness Detection
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>eKYC Demo — MediaPipe + FastAPI</p>
          </div>
          {sessionId && (
            <div style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>
              session: {sessionId.slice(0, 16)}…
              <StatusBadge status={sessionStatus} />
            </div>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20, alignItems: "start" }}>
          {/* Left: video + controls */}
          <div>
            {/* Video */}
            <div style={{
              position: "relative",
              background: "#0a0f1a",
              borderRadius: 16,
              overflow: "hidden",
              border: "1px solid #1e293b",
              aspectRatio: "4/3",
            }}>
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }}
              />
              <canvas ref={canvasRef} style={{ display: "none" }} />

              {/* Overlay: current challenge instruction */}
              {isStreaming && currentChallenge && (
                <div style={{
                  position: "absolute", bottom: 0, left: 0, right: 0,
                  background: "linear-gradient(transparent, rgba(0,0,0,0.85))",
                  padding: "32px 20px 16px",
                  textAlign: "center",
                }}>
                  <div style={{ fontSize: 13, color: "#94a3b8", marginBottom: 4 }}>
                    Challenge {currentChallengeIndex + 1} of {challenges.length}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: "#60a5fa" }}>
                    {currentChallenge.instruction}
                  </div>
                </div>
              )}

              {/* Overlay: face status */}
              {isStreaming && frameData && (
                <div style={{
                  position: "absolute", top: 12, left: 12,
                  display: "flex", gap: 8, flexWrap: "wrap",
                }}>
                  <Pill color={frameData.face_detected && frameData.face_count === 1 ? "#4ade80" : "#f87171"}>
                    {frameData.face_detected ? `${frameData.face_count} face${frameData.face_count !== 1 ? "s" : ""}` : "No face"}
                  </Pill>
                  {frameData.spoof_detected && <Pill color="#fb923c">Spoof!</Pill>}
                </div>
              )}

              {/* Timer */}
              {isStreaming && (
                <div style={{ position: "absolute", top: 12, right: 12, fontSize: 13, color: "#94a3b8", fontVariantNumeric: "tabular-nums" }}>
                  {elapsed}s
                </div>
              )}

              {/* Idle placeholder */}
              {phase === "idle" && (
                <div style={{
                  position: "absolute", inset: 0, display: "flex",
                  flexDirection: "column", alignItems: "center", justifyContent: "center",
                  color: "#334155", gap: 12,
                }}>
                  <svg width={60} height={60} fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <circle cx={12} cy={8} r={4} /><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                  </svg>
                  <span style={{ fontSize: 14 }}>Camera preview will appear here</span>
                </div>
              )}
            </div>

            {/* Spoof score bar */}
            {isStreaming && frameData?.spoof_score > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#64748b", marginBottom: 4 }}>
                  <span>Spoof Score</span>
                  <span style={{ color: frameData.spoof_score > 0.6 ? "#f87171" : "#4ade80" }}>
                    {(frameData.spoof_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div style={{ height: 6, background: "#1e293b", borderRadius: 99, overflow: "hidden" }}>
                  <div style={{
                    height: "100%",
                    width: `${frameData.spoof_score * 100}%`,
                    background: frameData.spoof_score > 0.6 ? "#ef4444" : "#4ade80",
                    borderRadius: 99,
                    transition: "width 0.3s, background 0.3s",
                  }} />
                </div>
              </div>
            )}

            {/* Controls */}
            <div style={{ display: "flex", gap: 10, marginTop: 16, alignItems: "center" }}>
              <input
                value={userId}
                onChange={e => setUserId(e.target.value)}
                placeholder="User ID (optional)"
                disabled={phase !== "idle"}
                style={{
                  flex: 1, padding: "10px 14px", borderRadius: 10,
                  background: "#1e293b", border: "1px solid #334155",
                  color: "#e2e8f0", fontSize: 14, outline: "none",
                }}
              />
              {phase === "idle" && (
                <Btn onClick={startSession} color="#3b82f6">Start Session</Btn>
              )}
              {(isStreaming || isDone) && (
                <Btn onClick={reset} color="#64748b">Reset</Btn>
              )}
              {phase === "starting" && (
                <Btn color="#64748b" disabled>Starting…</Btn>
              )}
            </div>

            {error && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: 10, color: "#f87171", fontSize: 13 }}>
                {error}
              </div>
            )}
          </div>

          {/* Right panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Result */}
            {isDone && result && (
              <div style={{ padding: 20, background: "#0f172a", border: `1px solid ${result.passed ? "#166534" : "#7f1d1d"}`, borderRadius: 16, textAlign: "center" }}>
                <ScoreGauge score={result.liveness_score ?? result.liveness_score} passed={result.passed} />
                {sessionId && (
                  <button
                    onClick={fetchResult}
                    style={{ marginTop: 14, fontSize: 12, color: "#60a5fa", background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}
                  >
                    Fetch full result from REST
                  </button>
                )}
                {result.challenges_completed !== undefined && (
                  <div style={{ marginTop: 10, fontSize: 12, color: "#64748b" }}>
                    Challenges: {result.challenges_completed}/{result.challenges_total} &nbsp;|&nbsp;
                    Avg spoof: {(result.avg_spoof_score * 100 || 0).toFixed(1)}%
                    {result.duration_seconds && ` | ${result.duration_seconds.toFixed(1)}s`}
                  </div>
                )}
              </div>
            )}

            {/* Challenges */}
            {challenges.length > 0 && (
              <div style={{ padding: 16, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Challenges
                </div>
                <ChallengeList
                  challenges={challenges}
                  completedCount={completedCount}
                  currentIndex={isDone ? challenges.length : currentChallengeIndex}
                />
              </div>
            )}

            {/* Live stats */}
            {isStreaming && frameData && (
              <div style={{ padding: 16, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Live Frame Data
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <Stat label="Face detected" value={frameData.face_detected ? "Yes" : "No"} ok={frameData.face_detected} />
                  <Stat label="Face count" value={frameData.face_count} ok={frameData.face_count === 1} />
                  <Stat label="Spoof detected" value={frameData.spoof_detected ? "YES" : "No"} ok={!frameData.spoof_detected} />
                  {frameData.message && (
                    <div style={{ fontSize: 12, color: "#60a5fa", marginTop: 4, fontStyle: "italic" }}>
                      {frameData.message}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Log */}
            <div style={{ padding: 16, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#64748b", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Log
              </div>
              <div style={{ maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 3 }}>
                {log.length === 0 && <span style={{ fontSize: 12, color: "#334155" }}>No events yet.</span>}
                {log.map((entry, i) => (
                  <div key={i} style={{ fontSize: 11, color: entry.type === "error" ? "#f87171" : entry.type === "success" ? "#4ade80" : "#64748b", fontFamily: "monospace" }}>
                    <span style={{ color: "#334155" }}>{entry.ts}</span> {entry.msg}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── small sub-components ──────────────────────────────────────────────────────
function Pill({ color, children }) {
  return (
    <span style={{
      background: `${color}22`,
      color,
      border: `1px solid ${color}55`,
      borderRadius: 99,
      padding: "2px 10px",
      fontSize: 12,
      fontWeight: 600,
    }}>
      {children}
    </span>
  );
}

function Btn({ onClick, color, children, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "10px 20px",
        borderRadius: 10,
        background: disabled ? "#1e293b" : color,
        color: disabled ? "#475569" : "#fff",
        border: "none",
        fontWeight: 600,
        fontSize: 14,
        cursor: disabled ? "default" : "pointer",
        whiteSpace: "nowrap",
        transition: "opacity 0.2s",
      }}
    >
      {children}
    </button>
  );
}

function Stat({ label, value, ok }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
      <span style={{ color: "#64748b" }}>{label}</span>
      <span style={{ color: ok ? "#4ade80" : "#f87171", fontWeight: 600 }}>{String(value)}</span>
    </div>
  );
}
