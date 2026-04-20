// Design tokens — EY theme colors (yellow, white, grey)
var C = {
  bg:          '#ffffff',        // White background
  surface:     '#f8f9fa',        // Light grey surface
  card:        '#ffffff',        // White cards
  border:      '#e9ecef',        // Light grey borders
  accent:      '#ffd100',        // EY yellow
  accentSoft:  'rgba(255,209,0,0.12)',  // Soft yellow
  accentGlow:  'rgba(255,209,0,0.30)',  // Yellow glow
  green:       '#28a745',        // Success green
  greenSoft:   'rgba(40,167,69,0.12)',  // Soft green
  amber:       '#ffc107',        // Warning amber
  amberSoft:   'rgba(255,193,7,0.12)',  // Soft amber
  red:         '#dc3545',         // Error red
  redSoft:     'rgba(220,53,69,0.12)',  // Soft red
  purple:      '#6f42c1',         // Purple accent
  purpleSoft:  'rgba(111,66,193,0.12)', // Soft purple
  text:        '#212529',         // Dark grey text
  textMuted:   '#6c757d',         // Medium grey text
  textDim:     '#adb5bd',         // Light grey text
  grey:        '#495057',         // EY grey
  greyLight:   '#dee2e6',         // Light grey
  greyDark:    '#343a40',         // Dark grey
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
    color: active ? '#ffffff' : C.text,
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
    background: active ? c : C.bg,
    color: active ? '#ffffff' : C.text,
    transition: 'all 0.15s',
  };
}

export { C, tabStyle, innerTabStyle };