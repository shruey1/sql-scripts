var C = {
  green:        '#28a745',
  greenSoft:    'rgba(40,167,69,0.12)',
  red:          '#dc3545',
  redSoft:      'rgba(220,53,69,0.12)',
  amber:        '#ffc107',
  accent:       '#ffd100',
  textMuted:    '#6c757d',
  textDim:      '#adb5bd',
};

function Section({ color, label, items }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <p
        style={{
          color: color,
          fontWeight: 700,
          fontSize: 11,
          marginBottom: 6,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        {label}
      </p>

      {items.map(function (item, i) {
        return (
          <p
            key={i}
            style={{
              color: C.textDim,
              fontSize: 13,
              margin: '3px 0',
              paddingLeft: 12,
              borderLeft: '2px solid ' + color,
            }}
          >
            {item}
          </p>
        );
      })}
    </div>
  );
}

export function ValidationPanel({ result }) {
  if (!result) return null;

  var is_valid = result.is_valid;
  var score = result.score;
  var errors = result.errors || [];
  var warnings = result.warnings || [];
  var suggestions = result.suggestions || [];

  return (
    <div
      style={{
        background: is_valid ? C.greenSoft : C.redSoft,
        border: '1px solid ' + (is_valid ? C.green : C.red) + '44',
        borderRadius: 12,
        padding: 20,
        marginBottom: 20,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          marginBottom:
            errors.length || warnings.length || suggestions.length ? 14 : 0,
        }}
      >
        <span style={{ fontSize: 22 }}>
          {is_valid ? '✅' : '❌'}
        </span>

        <div>
          <p
            style={{
              fontWeight: 700,
              color: is_valid ? C.green : C.red,
              margin: 0,
            }}
          >
            {is_valid
              ? 'Model validated successfully'
              : 'Validation failed'}
          </p>

          {score !== undefined && (
            <p
              style={{
                color: C.textMuted,
                fontSize: 12,
                margin: '2px 0 0',
              }}
            >
              Quality score: {score}/100
            </p>
          )}
        </div>
      </div>

      {errors.length > 0 && (
        <Section color={C.red} label="Errors" items={errors} />
      )}

      {warnings.length > 0 && (
        <Section color={C.amber} label="Warnings" items={warnings} />
      )}

      {suggestions.length > 0 && (
        <Section color={C.accent} label="Suggestions" items={suggestions} />
      )}
    </div>
  );
}