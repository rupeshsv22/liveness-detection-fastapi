export default function ScoreGauge({ score, passed }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = passed ? "#4ade80" : "#f87171";
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div style={{ textAlign: "center" }}>
      <svg width={130} height={130} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={65} cy={65} r={r} fill="none" stroke="#1e293b" strokeWidth={10} />
        <circle
          cx={65} cy={65} r={r}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div style={{ marginTop: -96, fontSize: 28, fontWeight: 700, color }}>
        {score.toFixed(1)}
      </div>
      <div style={{ marginTop: 70, fontSize: 13, color: "#94a3b8" }}>Liveness Score</div>
      <div style={{ marginTop: 6, fontSize: 18, fontWeight: 700, color }}>
        {passed ? "✓ PASSED" : "✗ FAILED"}
      </div>
    </div>
  );
}
