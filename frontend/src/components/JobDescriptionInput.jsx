import { useId } from 'react';
import SampleChips from './SampleChips.jsx';
import { MAX_JD_CHARS, MIN_JD_CHARS } from '../utils/validation.js';

/** Job description textarea with a live character counter, a Clear button and sample chips. */
export default function JobDescriptionInput({ value, onChange, textareaRef }) {
  const id = useId();
  const length = value.trim().length;
  const tooShort = length > 0 && length < MIN_JD_CHARS;
  const tooLong = length > MAX_JD_CHARS;

  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        Job description
      </label>
      <textarea
        id={id}
        ref={textareaRef}
        className="textarea"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Paste the full job description here."
        aria-describedby={`${id}-counter`}
        aria-invalid={tooLong || tooShort}
      />
      <div className="field__row">
        <span
          id={`${id}-counter`}
          className={`counter${tooShort || tooLong ? ' counter--bad' : ''}`}
          aria-live="polite"
        >
          {length.toLocaleString()} / {MAX_JD_CHARS.toLocaleString()} characters
          {tooShort && ` (minimum ${MIN_JD_CHARS})`}
        </span>
        <button type="button" className="btn btn--ghost btn--small" onClick={() => onChange('')} disabled={!value}>
          Clear
        </button>
      </div>
      <SampleChips onPick={onChange} />
    </div>
  );
}
