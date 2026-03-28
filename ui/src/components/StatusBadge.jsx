const COLOR = {
  PENDING:     { bg: "#1e293b", text: "#94a3b8" },
  IN_PROGRESS: { bg: "#1e3a5f", text: "#60a5fa" },
  COMPLETED:   { bg: "#14532d", text: "#4ade80" },
  FAILED:      { bg: "#450a0a", text: "#f87171" },
  EXPIRED:     { bg: "#292524", text: "#a8a29e" },
};

export default function StatusBadge({ status }) {
  const c = COLOR[status] ?? COLOR.PENDING;
  return (
    <span style={{
      background: c.bg,
      color: c.text,
      padding: "3px 10px",
      borderRadius: 99,
      fontSize: 12,
      fontWeight: 600,
      letterSpacing: "0.05em",
      textTransform: "uppercase",
    }}>
      {status}
    </span>
  );
}
