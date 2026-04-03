import { Btn } from './Primitives';

const C = {
  surface: '#13161e',
  border: '#232840',
  accent: '#4f8ef7',
  purple: '#a78bfa',
  text: '#e2e8f0',
  textMuted: '#64748b',
};

const STEPS = ['Describe', 'Review Model', 'SQL Scripts', 'ERD'];

export function Header({ step, onReset }) {
  return (
    <>
      {/* Top navigation bar */}
      <div
        style={{
          borderBottom: '1px solid ' + C.border,
          padding: '0 40px',
          background: C.surface,
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            height: 64,
            gap: 16,
          }}
        >
          {/* Logo + Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background:
                  'linear-gradient(135deg, ' +
                  C.accent +
                  ', ' +
                  C.purple +
                  ')',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
              }}
            >
              ⬡
            </div>

            <div>
              <p
                style={{
                  fontWeight: 700,
                  fontSize: 15,
                  letterSpacing: '-0.02em',
                }}
              >
                SchemaGen
              </p>
              <p
                style={{
                  fontSize: 11,
                  color: C.textMuted,
                  marginTop: -2,
                }}
              >
                Agentic Data Modelling
              </p>
            </div>
          </div>

          {/* Reset/New Model */}
          {step > 0 && (
            <div style={{ marginLeft: 'auto' }}>
              <Btn
                variant="ghost"
                onClick={onReset}
                style={{ padding: '7px 16px', fontSize: 13 }}
              >
                ← New Model
              </Btn>
            </div>
          )}
        </div>
      </div>

      {/* Step progress bar */}
      <div
        style={{
          borderBottom: '1px solid ' + C.border,
          background: C.surface,
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: '0 auto',
            padding: '12px 40px',
            display: 'flex',
            alignItems: 'center',
            overflowX: 'auto',
          }}
        >
          {STEPS.map((label, i) => (
            <div
              key={label}
              style={{
                display: 'flex',
                alignItems: 'center',
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                {/* Step circle */}
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    fontWeight: 700,
                    background: step >= i ? C.accent : C.border,
                    color: step >= i ? '#fff' : C.textMuted,
                    transition: 'all 0.3s',
                  }}
                >
                  {i + 1}
                </div>

                {/* Step label */}
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: step >= i ? C.text : C.textMuted,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </span>
              </div>

              {/* Connecting Line */}
              {i < STEPS.length - 1 && (
                <div
                  style={{
                    width: 40,
                    height: 1,
                    background: step > i ? C.accent : C.border,
                    margin: '0 16px',
                    transition: 'background 0.3s',
                    flexShrink: 0,
                  }}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}