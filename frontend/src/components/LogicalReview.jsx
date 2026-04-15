import { useState } from "react";
import { Btn, ErrorBanner } from "./ui/Primitives";
import { generateLogicalModel } from "../api/client";

const C = {
  surface: "#13161e",
  card: "#181c27",
  border: "#232840",
  accent: "#4f8ef7",
  green: "#34d399",
  purple: "#a78bfa",
  amber: "#fbbf24",
  text: "#e2e8f0",
  textMuted: "#64748b",
  textDim: "#94a3b8",
  teal: "#2dd4bf",
  red: "#f87171",
};

function modelTypeStyle(active, color) {
  const c = color || C.accent;
  return {
    flex: 1,
    padding: "14px 16px",
    borderRadius: 10,
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    border: "2px solid " + (active ? c : C.border),
    background: active ? c + "15" : C.card,
    color: active ? c : C.textMuted,
    transition: "all 0.15s",
    textAlign: "center",
  };
}

function EntityCard({ entity }) {
  const [open, setOpen] = useState(true);

  return (
    <div
      style={{
        background: C.card,
        border: "1px solid " + C.border,
        borderRadius: 12,
        marginBottom: 12,
        overflow: "hidden",
      }}
    >
      <div
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          cursor: "pointer",
          borderBottom: open ? "1px solid " + C.border : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 16 }}>⬡</span>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{entity.name}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              fontSize: 11,
              color: C.textMuted,
              background: C.surface,
              padding: "2px 8px",
              borderRadius: 6,
              border: "1px solid " + C.border,
            }}
          >
            {entity.attributes?.length || 0} attributes
          </span>
          <span style={{ color: C.textMuted, fontSize: 12 }}>
            {open ? "▲" : "▼"}
          </span>
        </div>
      </div>

      {open && (
        <div style={{ padding: "12px 16px" }}>
          {entity.description && (
            <p
              style={{
                fontSize: 12,
                color: C.textDim,
                marginBottom: 12,
                lineHeight: 1.5,
              }}
            >
              {entity.description}
            </p>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(entity.attributes || []).map((attr) => (
              <div
                key={attr.name}
                style={{
                  display: "flex",
                  gap: 10,
                  padding: "8px 10px",
                  background: C.surface,
                  borderRadius: 8,
                  border: "1px solid " + C.border,
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                      style={{ fontSize: 13, fontWeight: 600, color: C.text }}
                    >
                      {attr.name}
                    </span>

                    {attr.is_identifier && (
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          color: C.amber,
                          background: C.amber + "18",
                          padding: "1px 6px",
                          borderRadius: 4,
                          border: "1px solid " + C.amber + "40",
                        }}
                      >
                        PK
                      </span>
                    )}

                    {attr.is_required && !attr.is_identifier && (
                      <span
                        style={{
                          fontSize: 10,
                          color: C.textMuted,
                          background: C.card,
                          padding: "1px 6px",
                          borderRadius: 4,
                          border: "1px solid " + C.border,
                        }}
                      >
                        required
                      </span>
                    )}
                  </div>

                  {attr.description && (
                    <p
                      style={{
                        fontSize: 11,
                        color: C.textMuted,
                        marginTop: 2,
                        lineHeight: 1.4,
                      }}
                    >
                      {attr.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RelationshipList({ relationships }) {
  if (!relationships?.length) return null;

  return (
    <div style={{ marginTop: 20 }}>
      <p
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: C.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 10,
        }}
      >
        Relationships
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {relationships.map((r, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              background: C.card,
              border: "1px solid " + C.border,
              borderRadius: 8,
              fontSize: 12,
            }}
          >
            <span style={{ color: C.accent, fontWeight: 700 }}>
              {r.from_entity}
            </span>
            <span style={{ color: C.textMuted }}>
              {r.label ? `— ${r.label} →` : "→"}
            </span>
            <span style={{ color: C.green, fontWeight: 700 }}>
              {r.to_entity}
            </span>
            <span
              style={{
                marginLeft: "auto",
                fontSize: 10,
                color: C.textMuted,
                background: C.surface,
                padding: "1px 6px",
                borderRadius: 4,
                border: "1px solid " + C.border,
              }}
            >
              {r.cardinality}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LogicalReview({
  logicalModel,
  userQuery,
  dbEngine,
  loading,
  error,
  onApprove,
}) {
  const [modelType, setModelType] = useState("both");
  const [feedback, setFeedback] = useState("");
  const [localModel, setLocalModel] = useState(logicalModel);
  const [iterating, setIterating] = useState(false);
  const [iterError, setIterError] = useState("");

  const entities = localModel?.entities || [];
  const relationships = localModel?.relationships || [];

  async function handleIterate() {
    if (!feedback.trim()) return;
    setIterating(true);
    setIterError("");

    try {
      const res = await generateLogicalModel(
        userQuery + "\n\nAdditional changes: " + feedback,
        dbEngine
      );
      setLocalModel(res.logical_model);
      setFeedback("");
    } catch (e) {
      setIterError(e.message);
    } finally {
      setIterating(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        gap: 24,
        alignItems: "flex-start",
        maxWidth: 1100,
        margin: "0 auto",
      }}
    >
      {/* LEFT */}
      <div style={{ flex: 1 }}>
        {entities.map((e) => (
          <EntityCard key={e.name} entity={e} />
        ))}

        <RelationshipList relationships={relationships} />
        <ErrorBanner message={error} />
      </div>

      {/* RIGHT */}
      <div style={{ width: 300 }}>
        <Btn
          onClick={() => onApprove(modelType, localModel)}
          loading={loading}
          disabled={entities.length === 0}
        >
          Approve & Generate Physical Model →
        </Btn>
      </div>
    </div>
  );
}
