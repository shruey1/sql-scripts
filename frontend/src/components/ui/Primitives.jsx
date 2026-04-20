// components/ui/Primitives.jsx

// NOTE: C is defined locally here to avoid any import resolution issues
const C = {
  bg:         '#ffffff',
  surface:    '#f8f9fa',
  card:       '#ffffff',
  border:     '#e9ecef',
  accent:     '#ffd100',
  accentSoft: 'rgba(255,209,0,0.12)',
  green:      '#28a745',
  greenSoft:  'rgba(40,167,69,0.12)',
  amber:      '#ffc107',
  red:        '#dc3545',
  redSoft:    'rgba(220,53,69,0.12)',
  purple:     '#6f42c1',
  text:       '#212529',
  textMuted:  '#6c757d',
  textDim:    '#adb5bd',
};

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size }) {
  const s = size || 20;
  return (
    <svg
      width={s}
      height={s}
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: 'spin 0.8s linear infinite', flexShrink: 0 }}
    >
      <circle cx="12" cy="12" r="10" stroke="#ffffff22" strokeWidth="3" />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke={C.accent}
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ color, children, style }) {
  const col = color || C.accent;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 10px',
        borderRadius: 20,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        background: col + '22',
        color: col,
        border: '1px solid ' + col + '44',
        ...style,
      }}
    >
      {children}
    </span>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
export function Btn({ onClick, disabled, loading, children, variant, style }) {
  const v = variant || 'primary';

  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 22px',
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 600,
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.55 : 1,
    border: 'none',
    transition: 'all 0.15s',
    letterSpacing: '0.02em',
    outline: 'none',
    whiteSpace: 'nowrap',
  };

  const variants = {
    primary: { background: C.accent, color: '#fff' },
    ghost:   { background: C.accentSoft, color: C.accent, border: '1px solid ' + C.border },
    danger:  { background: C.redSoft, color: C.red, border: '1px solid ' + C.red + '44' },
    success: { background: C.greenSoft, color: C.green, border: '1px solid ' + C.green + '44' },
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{ ...base, ...(variants[v] || variants.primary), ...style }}
    >
      {loading && <Spinner size={15} />}
      {children}
    </button>
  );
}

// ── Error banner ──────────────────────────────────────────────────────────────
export function ErrorBanner({ message }) {
  if (!message) return null;

  return (
    <div
      style={{
        padding: '12px 16px',
        background: C.redSoft,
        border: '1px solid ' + C.red + '44',
        borderRadius: 8,
        color: C.red,
        fontSize: 13,
        marginBottom: 16,
      }}
    >
      ⚠ {message}
    </div>
  );
}