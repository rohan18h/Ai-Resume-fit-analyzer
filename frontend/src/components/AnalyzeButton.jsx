import { useId } from 'react';

/** The Analyze button. When disabled, the reason is shown next to it. */
export default function AnalyzeButton({ disabledReason, onClick }) {
  const reasonId = useId();
  return (
    <div className="analyze-row">
      <button
        type="button"
        className="btn btn--primary btn--large"
        onClick={onClick}
        disabled={Boolean(disabledReason)}
        aria-describedby={disabledReason ? reasonId : undefined}
      >
        Analyze
      </button>
      {disabledReason && (
        <p className="analyze-row__reason" id={reasonId}>
          {disabledReason}
        </p>
      )}
    </div>
  );
}
