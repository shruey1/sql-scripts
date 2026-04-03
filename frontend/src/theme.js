// Design tokens — single source of truth for all colours & shared styles
var C = {
  bg:          '#0d0f14',
  surface:     '#13161e',
  card:        '#181c27',
  border:      '#232840',
  accent:      '#4f8ef7',
  accentSoft:  'rgba(79,142,247,0.12)',
  accentGlow:  'rgba(79,142,247,0.30)',
  green:       '#34d399',
  greenSoft:   'rgba(52,211,153,0.12)',
  amber:       '#fbbf24',
  amberSoft:   'rgba(251,191,36,0.12)',
  red:         '#f87171',
  redSoft:     'rgba(248,113,113,0.12)',
  purple:      '#a78bfa',
  purpleSoft:  'rgba(167,139,250,0.12)',
  text:        '#e2e8f0',
  textMuted:   '#64748b',
  textDim:     '#94a3b8',
};

function tabStyle(active, color) {
  var c = color || C.accent;
  return {
    padding: '10px 24px',
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
    background: active ? c : 'transparent',
    color: active ? '#fff' : C.textMuted,
    transition: 'all 0.15s',
    letterSpacing: '0.02em',
  };
}

function innerTabStyle(active, color) {
  var c = color || C.accent;
  return {
    padding: '7px 18px',
    borderRadius: 8,
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    border: '1px solid ' + (active ? c : C.border),
    background: active ? c + '18' : 'transparent',
    color: active ? c : C.textMuted,
    transition: 'all 0.15s',
  };
}

export { C, tabStyle, innerTabStyle };