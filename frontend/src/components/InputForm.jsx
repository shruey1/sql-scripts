// components/InputForm.jsx

import { useState } from "react";
import { Btn, ErrorBanner } from "./ui/Primitives";

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
};

function tabStyle(active) {
  return {
    padding: "10px 24px",
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    border: "none",
    background: active ? C.accent : "transparent",
    color: active ? "#fff" : C.textMuted,
    transition: "all 0.15s",
    letterSpacing: "0.02em",
  };
}

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

const DB_ENGINES = [
  "MySQL",
  "PostgreSQL",
  "MSSQL",
  "BigQuery",
  "Snowflake",
  "SQLite",
  "Redshift",
];

// ── Summary UI ─────────────────────────────────────────────────────────────

function SummaryRow({ label, value, accent }) {
  const lines = value.split('\n').filter(line => line.trim());
  const isList = lines.some(line => line.trim().startsWith('-'));

  return (
    <div style={{ marginBottom: 16 }}>
      <p
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: C.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: 8,
        }}
      >
        {label}
      </p>
      {isList ? (
        <ul
          style={{
            fontSize: 12,
            color: accent || C.text,
            lineHeight: 1.6,
            margin: 0,
            paddingLeft: 20,
            listStyleType: 'disc',
          }}
        >
          {lines.map((line, i) => (
            <li key={i} style={{ marginBottom: 4 }}>
              {line.replace(/^- /, '')}
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ fontSize: 12, color: accent || C.textDim, lineHeight: 1.5 }}>
          {value}
        </p>
      )}
    </div>
  );
}

const RELATIONAL_PROMPT = `

- Applies 3rd Normal Form (3NF) unless the domain clearly benefits from denormalisation.
- Every table has a primary key.
- Expresses all foreign-key relationships explicitly.
- Use standard SQL data types (VARCHAR, INT, BIGINT, DECIMAL, DATE, TIMESTAMP, BOOLEAN, TEXT, UUID).
- Include NOT NULL, UNIQUE, and CHECK constraints where appropriate.
- Outputs structured JSON only.
`;

const ANALYTICAL_PROMPT = `

- Designs a star schema with one or more central fact tables surrounded by dimension tables.
- Fact tables hold measurable, numeric metrics (measures) and foreign keys to dimensions.
- Dimension tables hold descriptive attributes (slowly changing dimensions are acceptable).
- Includes a DATE/TIME dimension if time-series analysis is relevant.
- Uses surrogate integer keys (e.g. customer_key, date_key) as primary keys in dimension tables.
- Outputs structured JSON only.
`;

function PromptSummaryPanel({ modelType }) {
  return (
    <div style={{ padding: "4px 0" }}>
      {(modelType === "both" || modelType === "relational") && (
        <div style={{ marginBottom: 20 }}>
          <SummaryRow label="Relational Model Rules" value={RELATIONAL_PROMPT.trim()} />
        </div>
      )}

      {(modelType === "both" || modelType === "analytical") && (
        <div>
          <SummaryRow label="Analytical Model Rules" value={ANALYTICAL_PROMPT.trim()} />
        </div>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────

export function InputForm({ onSubmit, loading, error }) {
  const [mainTab, setMainTab] = useState("new");
  const [prompt, setPrompt] = useState("");
  const [uploadedSchema, setUploadedSchema] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [validationMode, setValidationMode] = useState("auto");
  const [modelType, setModelType] = useState("both");
  const [dbEngine, setDbEngine] = useState("");
  const [customKb, setCustomKb] = useState(null);
  const [customKbFileName, setCustomKbFileName] = useState("");

  // File upload
  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadedFileName(file.name);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        setUploadedSchema(JSON.parse(ev.target.result));
      } catch {
        setUploadedSchema({ raw: ev.target.result });
      }
    };
    reader.readAsText(file);
  }

  function handleKbFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setCustomKbFileName(file.name);

    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        setCustomKb(JSON.parse(ev.target.result));
      } catch {
        setCustomKb({ raw: ev.target.result });
      }
    };
    reader.readAsText(file);
  }

  const canSubmit =
    prompt.trim().length > 0 &&
    (mainTab === "new" || uploadedSchema !== null);

  function handleSubmit() {
    if (!canSubmit) return;

    onSubmit({
      userQuery: prompt,
      operation: mainTab === "new" ? "CREATE" : "MODIFY",
      existingModel: mainTab === "modify" ? uploadedSchema : null,
      validationMode: validationMode,
      modelType: "both",
      dbEngine: dbEngine,
      customKb: customKb,
    });
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
    <div>  
      {/* LEFT SIDE — FORM */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: 6,
            background: C.surface,
            padding: 6,
            borderRadius: 12,
            border: "1px solid " + C.border,
            marginBottom: 28,
            width: "fit-content",
          }}
        >
          <button
            style={tabStyle(mainTab === "new")}
            onClick={() => setMainTab("new")}
          >
            ✦ New Schema
          </button>

          <button
            style={tabStyle(mainTab === "modify")}
            onClick={() => setMainTab("modify")}
          >
            ⟳ Modify Existing
          </button>
        </div>

        {/* Card */}
        <div
          style={{
            background: C.surface,
            border: "1px solid " + C.border,
            borderRadius: 16,
            padding: 28,
          }}
        >
          {/* HEADER */}
          <p style={{ fontWeight: 700, fontSize: 18, marginBottom: 6 }}>
            {mainTab === "new"
              ? "Describe your data model"
              : "Describe your changes"}
          </p>

          <p
            style={{
              color: C.textMuted,
              fontSize: 14,
              marginBottom: 20,
              lineHeight: 1.6,
            }}
          >
            {mainTab === "new"
              ? 'Describe what you need. Mention the database engine (e.g. "PostgreSQL") if you want — otherwise MySQL is used.'
              : "Describe what changes you want. Mention the DB engine if needed."}
          </p>

          {/* TEXTAREA */}
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              mainTab === "new"
                ? 'e.g. I need a PostgreSQL schema for an e‑commerce platform…'
                : "e.g. Add a reviews table and an address column to customers…"
            }
            style={{
              width: "100%",
              minHeight: 130,
              background: C.card,
              border: "1px solid " + C.border,
              borderRadius: 10,
              padding: 16,
              fontSize: 14,
              color: C.text,
              resize: "vertical",
              outline: "none",
              lineHeight: 1.6,
            }}
          />

          {/* MODEL TYPE SELECTOR */}
          {/* <div style={{ marginTop: 20 }}>
            <p
              style={{
                color: C.textMuted,
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 10,
              }}
            >
              Model type to generate
            </p> */}

            
          </div>

          {/* ENGINE SELECTOR */}
          <div style={{ marginTop: 20 }}>
            <p
              style={{
                color: C.textMuted,
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 10,
              }}
            >
              Database engine
              <span
                style={{
                  color: C.textDim,
                  fontWeight: 400,
                  marginLeft: 8,
                }}
              >
                (auto-detected from your prompt, or pick one)
              </span>
            </p>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <button
                onClick={() => setDbEngine("")}
                style={{
                  padding: "7px 16px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  border:
                    "1px solid " +
                    (dbEngine === "" ? C.amber : C.border),
                  background:
                    dbEngine === "" ? C.amber + "18" : C.card,
                  color: dbEngine === "" ? C.amber : C.textMuted,
                  transition: "all 0.15s",
                }}
              >
                Auto-detect
              </button>

              {DB_ENGINES.map((eng) => {
                const active = dbEngine === eng;
                return (
                  <button
                    key={eng}
                    onClick={() => setDbEngine(eng)}
                    style={{
                      padding: "7px 16px",
                      borderRadius: 8,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      border:
                        "1px solid " +
                        (active ? C.accent : C.border),
                      background: active
                        ? C.accent + "18"
                        : C.card,
                      color: active ? C.accent : C.textMuted,
                      transition: "all 0.15s",
                    }}
                  >
                    {eng}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Knowledge Base Upload */}
          <div style={{ marginTop: 20 }}>
            <p
              style={{
                color: C.textMuted,
                fontSize: 13,
                fontWeight: 600,
                marginBottom: 10,
              }}
            >
              Custom Knowledge Base (Optional)
              <span
                style={{
                  color: C.textDim,
                  fontWeight: 400,
                  marginLeft: 8,
                }}
              >
                Upload a JSON file with field descriptions for better schema generation
              </span>
            </p>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                background: C.card,
                border:
                  "2px dashed " +
                  (customKb ? C.green : C.border),
                borderRadius: 10,
                cursor: "pointer",
                transition: "border-color 0.2s",
              }}
            >
              <span style={{ fontSize: 20 }}>
                {customKb ? "✓" : "📚"}
              </span>

              <div>
                <p
                  style={{
                    fontWeight: 600,
                    fontSize: 13,
                    color: customKb ? C.green : C.textDim,
                  }}
                >
                  {customKbFileName || "Click to upload knowledge base JSON"}
                </p>

                {customKb && (
                  <p
                    style={{
                      fontSize: 11,
                      color: C.textMuted,
                      marginTop: 2,
                    }}
                  >
                    Knowledge base loaded successfully
                  </p>
                )}
              </div>

              <input
                type="file"
                accept=".json"
                onChange={handleKbFile}
                style={{ display: "none" }}
              />
            </label>
          </div>

          {/* Upload schema for modify */}
          {mainTab === "modify" && (
            <div style={{ marginTop: 20 }}>
              <p
                style={{
                  color: C.textMuted,
                  fontSize: 13,
                  marginBottom: 8,
                  fontWeight: 600,
                }}
              >
                Upload existing schema (JSON)
              </p>

              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 16px",
                  background: C.card,
                  border:
                    "2px dashed " +
                    (uploadedSchema ? C.green : C.border),
                  borderRadius: 10,
                  cursor: "pointer",
                  transition: "border-color 0.2s",
                }}
              >
                <span style={{ fontSize: 20 }}>
                  {uploadedSchema ? "✓" : "⬆"}
                </span>

                <div>
                  <p
                    style={{
                      fontWeight: 600,
                      fontSize: 13,
                      color: uploadedSchema ? C.green : C.textDim,
                    }}
                  >
                    {uploadedFileName || "Click to upload schema JSON"}
                  </p>

                  {uploadedSchema && (
                    <p
                      style={{
                        fontSize: 11,
                        color: C.textMuted,
                        marginTop: 2,
                      }}
                    >
                      Schema loaded successfully
                    </p>
                  )}
                </div>

                <input
                  type="file"
                  accept=".json"
                  onChange={handleFile}
                  style={{ display: "none" }}
                />
              </label>
            </div>
          )}

          {/* VALIDATION MODE */}
          <div
            style={{
              marginTop: 20,
              display: "flex",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <p
              style={{
                color: C.textMuted,
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              Validation mode:
            </p>

            <div
              style={{
                display: "flex",
                gap: 6,
                background: C.card,
                padding: 4,
                borderRadius: 8,
                border: "1px solid " + C.border,
              }}
            >
              {["auto", "manual"].map((m) => (
                <button
                  key={m}
                  onClick={() => setValidationMode(m)}
                  style={{
                    padding: "5px 14px",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: 600,
                    background:
                      validationMode === m ? C.accent : "transparent",
                    color: validationMode === m ? "#fff" : C.textMuted,
                    transition: "all 0.15s",
                    textTransform: "capitalize",
                  }}
                >
                  {m}
                </button>
              ))}
            </div>

            <p style={{ fontSize: 12, color: C.textMuted }}>
              {validationMode === "auto"
                ? "LLM validates and auto-corrects"
                : "You review and approve changes"}
            </p>
          </div>

          {/* ERROR MESSAGE */}
          <ErrorBanner message={error} />

          {/* SUBMIT BUTTON */}
          <div style={{ marginTop: 24 }}>
            <Btn onClick={handleSubmit} loading={loading} disabled={!canSubmit}>
              Generate Data Model →
            </Btn>
          </div>
        </div>
      </div>

      {/* RIGHT SIDE — SUMMARY PANEL */}
      <div
        style={{
          width: 300,
          flexShrink: 0,
          background: C.surface,
          border: "1px solid " + C.border,
          borderRadius: 16,
          padding: 20,
          position: "sticky",
          top: 32,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 16,
          }}
        >
          <span style={{ fontSize: 16 }}>⚙</span>
          <p style={{ fontWeight: 700, fontSize: 14 }}>Generation Rules</p>
        </div>

        <p
          style={{
            fontSize: 12,
            color: C.textMuted,
            marginBottom: 16,
            lineHeight: 1.5,
          }}
        >
          Rules that will be applied when your model is generated.
        </p>

        <div style={{ borderTop: "1px solid " + C.border, paddingTop: 16 }}>
          <PromptSummaryPanel modelType={modelType} />
        </div>
      </div>
    </div>
  );
}