import { useState, useMemo } from "react";
import { Btn, Badge } from "./ui/Primitives";
import { ValidationPanel } from "./ValidationPanel";

const C = {
  border: "#232840",
  accent: "#4f8ef7",
  green: "#34d399",
  purple: "#a78bfa",
  amber: "#fbbf24",
  teal: "#2dd4bf",
  textMuted: "#64748b",
  text: "#e2e8f0",
  card: "#181c27",
};

// Tabs to display — no combined_sql
const TAB_DEFS = [
  { key: "relational_sql", label: "Relational DDL", color: C.green },
  { key: "analytical_sql", label: "Analytical DDL", color: C.purple },
];

function innerTabStyle(active, color) {
  const c = color || C.accent;
  return {
    padding: "7px 18px",
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    border: "1px solid " + (active ? c : C.border),
    background: active ? c + "18" : "transparent",
    color: active ? c : C.textMuted,
    transition: "all 0.15s",
  };
}

function SQLBlock({ sql }) {
  const [copied, setCopied] = useState(false);

  if (!sql)
    return <p style={{ color: C.textMuted, padding: 20 }}>No SQL generated for this section.</p>;

  function copy() {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div style={{ position: "relative" }}>
      <div style={{ position: "absolute", top: 12, right: 12, zIndex: 10 }}>
        <Btn variant="ghost" onClick={copy} style={{ padding: "6px 14px", fontSize: 12 }}>
          {copied ? "✓ Copied" : "Copy"}
        </Btn>
      </div>

      <pre
        style={{
          background: "#090b10",
          border: "1px solid " + C.border,
          borderRadius: 12,
          padding: 20,
          overflowX: "auto",
          fontSize: 13,
          lineHeight: 1.7,
          color: "#c9d1d9",
          fontFamily: '"Fira Code", monospace',
          maxHeight: 520,
          overflowY: "auto",
        }}
      >
        <code>{sql}</code>
      </pre>
    </div>
  );
}

export function SQLView({
  sqlOutput,
  validation,
  onBack,
  onReset,
  onGenerateERD,
  erdLoading,
}) {
  const availableTabs = useMemo(() => {
    return TAB_DEFS.filter((t) => sqlOutput && sqlOutput[t.key]);
  }, [sqlOutput]);

  const [activeTab, setActiveTab] = useState(
    () => availableTabs[0]?.key || "relational_sql"
  );

  const activeTabDef =
    availableTabs.find((t) => t.key === activeTab) || availableTabs[0];

  // Download single SQL file
  function downloadSQL() {
    const sql = sqlOutput && sqlOutput[activeTab];
    if (!sql) return;

    const label =
      activeTabDef?.label?.replace(/\s+/g, "_").toLowerCase() || "sql";
    const dbType =
      sqlOutput?.db_type?.toLowerCase().replace(/\s+/g, "_") || "db";
    const filename = `${dbType}_${label}.sql`;

    const blob = new Blob([sql], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
  }

  // Download combined SQL
  function downloadAllSQL() {
    const combined = sqlOutput && sqlOutput.combined_sql;
    if (!combined) return;

    const dbType =
      sqlOutput?.db_type?.toLowerCase().replace(/\s+/g, "_") || "db";
    const filename = `${dbType}_combined_ddl.sql`;

    const blob = new Blob([combined], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
  }

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 24,
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 6,
              flexWrap: "wrap",
            }}
          >
            <h2 style={{ fontSize: 22, fontWeight: 700 }}>SQL Scripts</h2>
            <Badge color={C.green}>Ready</Badge>
            {sqlOutput && sqlOutput.db_type && (
              <Badge color={C.textMuted}>{sqlOutput.db_type}</Badge>
            )}
          </div>
          <p style={{ color: C.textMuted, fontSize: 14 }}>
            Production-ready DDL scripts generated from your validated data
            model.
          </p>
        </div>

        <Btn variant="ghost" onClick={onBack}>
          ← Back to Model
        </Btn>
      </div>

      {/* Validation */}
      {validation && <ValidationPanel result={validation} />}

      {/* Tabs + downloads */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {availableTabs.map((t) => (
            <button
              key={t.key}
              style={innerTabStyle(activeTabDef?.key === t.key, t.color)}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Download buttons */}
        <div style={{ display: "flex", gap: 8 }}>
          <Btn
            variant="ghost"
            onClick={downloadSQL}
            disabled={!sqlOutput || !sqlOutput[activeTab]}
            style={{
              fontSize: 12,
              padding: "6px 14px",
              border: "1px solid " + (activeTabDef?.color || C.accent),
              color: activeTabDef?.color || C.accent,
            }}
          >
            ⬇ Download {activeTabDef?.label || "SQL"}
          </Btn>

          {sqlOutput &&
            sqlOutput.relational_sql &&
            sqlOutput.analytical_sql && (
              <Btn
                variant="ghost"
                onClick={downloadAllSQL}
                style={{
                  fontSize: 12,
                  padding: "6px 14px",
                  border: "1px solid " + C.teal,
                  color: C.teal,
                }}
              >
                ⬇ Download All SQL
              </Btn>
            )}
        </div>
      </div>

      {/* SQL CONTENT */}
      <SQLBlock sql={sqlOutput && sqlOutput[activeTabDef?.key]} />

      {/* Action Bar */}
      <div
        style={{
          marginTop: 28,
          padding: "20px 24px",
          background: "#13161e",
          border: "1px solid " + C.border,
          borderRadius: 14,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
            Generate ER Diagram
          </p>
          <p style={{ color: C.textMuted, fontSize: 13 }}>
            Visualise your schema as an interactive entity-relationship diagram.
          </p>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <Btn variant="ghost" onClick={onReset}>
            ✦ Start New
          </Btn>

          <Btn
            onClick={() =>
              onGenerateERD(sqlOutput && sqlOutput.combined_sql)
            }
            loading={erdLoading}
            disabled={!sqlOutput || !sqlOutput.combined_sql}
            style={{
              background: "linear-gradient(135deg, #4f8ef7, #a78bfa)",
              color: "#fff",
              border: "none",
            }}
          >
            ⬡ Generate ERD →
          </Btn>
        </div>
      </div>
    </div>
  );
}