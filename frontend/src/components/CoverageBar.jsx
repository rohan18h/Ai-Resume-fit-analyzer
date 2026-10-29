/** "You match 5 of 8 required skills (62%)" with a progress bar. */
export default function CoverageBar({ matched, total, percentValue }) {
  const value = Math.round(percentValue);
  return (
    <div className="coverage">
      <p className="coverage__text">
        You match <strong>{matched}</strong> of <strong>{total}</strong> required skills ({value}%)
      </p>
      <div
        className="bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label="Skill coverage"
      >
        <div className="bar__fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
