const ICON = {
  BLINK:       "👁",
  BLINK_TWICE: "👀",
  TURN_LEFT:   "⬅️",
  TURN_RIGHT:  "➡️",
  NOD:         "↕️",
};

export default function ChallengeList({ challenges, completedCount, currentIndex }) {
  if (!challenges?.length) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {challenges.map((c, i) => {
        const done = i < completedCount;
        const active = i === currentIndex;
        return (
          <div
            key={c.order}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "10px 14px",
              borderRadius: 10,
              background: done ? "#14532d33" : active ? "#1e3a5f55" : "#1e293b",
              border: `1px solid ${done ? "#4ade8055" : active ? "#60a5fa55" : "#334155"}`,
              transition: "all 0.3s",
            }}
          >
            <span style={{ fontSize: 20 }}>{ICON[c.type] ?? "●"}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: done ? "#4ade80" : active ? "#60a5fa" : "#cbd5e1" }}>
                {c.type}
              </div>
              <div style={{ fontSize: 12, color: "#64748b" }}>{c.instruction}</div>
            </div>
            <span style={{ fontSize: 18 }}>
              {done ? "✅" : active ? "⏳" : "○"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
