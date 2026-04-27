const STEPS = [
  {
    num: "01",
    label: "Describe Domain",
    desc: "Define your business domain and entities in plain English",
  },
  {
    num: "02",
    label: "Logical Model",
    desc: "Review auto-generated entities, attributes and relationships",
  },
  {
    num: "03",
    label: "Physical Model",
    desc: "Map logical design to tables, types and constraints",
  },
  {
    num: "04",
    label: "Generate SQL",
    desc: "Export validated DDL for your chosen database engine",
  },
  {
    num: "05",
    label: "Export ERD",
    desc: "Download a publication-ready entity-relationship diagram",
  },
];
 
export function LandingPage({ onGetStarted }) {
  return (
    <div style={{
      height: "100vh",
      width: "100vw",
      background: "#2e2e38",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      position: "relative",
    }}>
 
      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .land-cta {
          background: #ffe600;
          color: #2e2e38;
          border: none;
          font-weight: 700;
          font-size: 1.08rem;
          padding: 15px 38px;
          cursor: pointer;
          letter-spacing: 0.02em;
          clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));
          transition: background 0.18s, transform 0.18s, box-shadow 0.18s;
          display: inline-flex; align-items: center; gap: 10px;
          font-family: inherit;
        }
        .land-cta:hover {
          background: #fff176;
          transform: translateY(-2px);
          box-shadow: 0 10px 32px rgba(255,230,0,0.3);
        }
        .step-chip {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 13px 16px;
          border: 1px solid rgba(255,255,255,0.08);
          background: rgba(255,255,255,0.03);
          animation: fade-in 0.5s ease both;
          transition: border-color 0.2s, background 0.2s;
          cursor: default;
        }
        .step-chip:hover {
          border-color: rgba(255,230,0,0.35);
          background: rgba(255,230,0,0.05);
        }
      `}</style>
 
      {/* ── Top bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "18px 48px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        animation: "fade-in 0.4s ease both",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, background: "#ffe600",
            clipPath: "polygon(0 0, 78% 0, 100% 22%, 100% 100%, 22% 100%, 0 78%)",
          }} />
          <span style={{ color: "#fff", fontWeight: 700, fontSize: "1.1rem", letterSpacing: "-0.01em" }}>
            SchemaGen
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#168736", animation: "pulse-dot 2s infinite" }} />
          <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "0.88rem", fontWeight: 500 }}>EY · Data Modelling Suite</span>
        </div>
      </div>
 
      {/* ── Main grid ── */}
      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: "1fr 1px 460px",
        overflow: "hidden",
        minHeight: 0,
      }}>
 
        {/* LEFT — hero */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 64px 0 80px",
          position: "relative",
          overflow: "hidden",
        }}>
          {/* Glow */}
          <div style={{
            position: "absolute", bottom: -100, left: -60,
            width: 420, height: 420,
            background: "radial-gradient(circle, rgba(255,230,0,0.07) 0%, transparent 70%)",
            pointerEvents: "none",
          }} />
 
          {/* Headline */}
          <h1 style={{
            fontSize: "clamp(2.8rem, 4.2vw, 4.4rem)",
            fontWeight: 800,
            color: "#ffffff",
            lineHeight: 1.05,
            letterSpacing: "-0.03em",
            marginBottom: "20px",
            animation: "fade-in 0.5s ease 0.15s both",
          }}>
            From idea to<br />
            <span style={{ color: "#ffe600", position: "relative", display: "inline-block" }}>
              production SQL
              <span style={{
                position: "absolute", bottom: 2, left: 0, right: 0,
                height: 3, background: "rgba(255,230,0,0.25)",
              }} />
            </span>
            <br />
            <span style={{ color: "rgba(255,255,255,0.28)", fontWeight: 700 }}>in five steps.</span>
          </h1>
 
          {/* Description */}
          <p style={{
            fontSize: "1.1rem",
            color: "rgba(255,255,255,0.42)",
            lineHeight: 1.75,
            maxWidth: "460px",
            marginBottom: "36px",
            animation: "fade-in 0.5s ease 0.25s both",
          }}>
            Describe your domain in plain English. Get validated DDL and an entity-relationship diagram — with full control at every stage.
          </p>
 
          {/* CTA */}
          <div style={{ animation: "fade-in 0.5s ease 0.35s both" }}>
            <button className="land-cta" onClick={onGetStarted}>
              Start modelling
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
 
          {/* Engine badges */}
          <div style={{
            display: "flex", alignItems: "center", gap: 7, flexWrap: "wrap",
            marginTop: "32px",
            animation: "fade-in 0.5s ease 0.45s both",
          }}>
            <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.22)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>
              Works with
            </span>
            {["MySQL", "PostgreSQL", "Snowflake", "SQL Server", "BigQuery"].map(e => (
              <span key={e} style={{
                fontSize: "0.76rem", fontWeight: 600, color: "rgba(255,255,255,0.35)",
                padding: "3px 10px", border: "1px solid rgba(255,255,255,0.09)",
                letterSpacing: "0.04em",
              }}>{e}</span>
            ))}
          </div>
        </div>
 
        {/* DIVIDER */}
        <div style={{ background: "rgba(255,255,255,0.07)" }} />
 
        {/* RIGHT — pipeline */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 40px 0 44px",
          gap: 6,
          background: "rgba(0,0,0,0.18)",
          position: "relative",
          overflow: "hidden",
        }}>
          {/* Section label */}
          <div style={{ marginBottom: "18px", animation: "fade-in 0.5s ease 0.2s both" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <div style={{ width: 22, height: 2, background: "#ffe600" }} />
              <span style={{ fontSize: "0.76rem", fontWeight: 700, color: "#ffe600", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                Pipeline
              </span>
            </div>
            <p style={{ color: "rgba(255,255,255,0.35)", fontSize: "0.9rem", fontWeight: 500 }}>
              Approve &amp; iterate at every stage
            </p>
          </div>
 
          {STEPS.map((s, i) => (
            <div
              key={i}
              className="step-chip"
              style={{ animationDelay: `${0.25 + i * 0.08}s` }}
            >
              {/* Step number */}
              <span style={{
                fontWeight: 800, fontSize: "0.72rem",
                color: "#ffe600", letterSpacing: "0.06em",
                minWidth: 24, paddingTop: 2,
              }}>{s.num}</span>
 
              <div style={{ width: 1, alignSelf: "stretch", background: "rgba(255,255,255,0.08)", flexShrink: 0 }} />
 
              {/* Text */}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "rgba(255,255,255,0.85)", marginBottom: 3 }}>
                  {s.label}
                </div>
                <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.35)", lineHeight: 1.5 }}>
                  {s.desc}
                </div>
              </div>
 
              <div style={{ paddingTop: 2, flexShrink: 0 }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="2.5">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </div>
            </div>
          ))}
 
        </div>
      </div>
 
      {/* ── Footer bar ── */}
      <div style={{
        padding: "12px 48px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        animation: "fade-in 0.4s ease 0.5s both",
        flexShrink: 0,
      }}>
        <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.15)", letterSpacing: "0.04em" }}>
          © EY · Enterprise Data Modelling
        </span>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {[1, 2, 3].map(i => (
            <div key={i} style={{
              width: i === 1 ? 20 : 6,
              height: 3,
              background: i === 1 ? "#ffe600" : "rgba(255,255,255,0.1)",
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}
 