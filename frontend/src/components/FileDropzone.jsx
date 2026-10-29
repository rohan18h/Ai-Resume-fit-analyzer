import { useId, useRef, useState } from 'react';
import Icon from './Icon.jsx';
import { formatBytes } from '../utils/format.js';
import { MAX_UPLOAD_MB } from '../utils/validation.js';

/** Drag-and-drop zone with a Browse button. Shows the picked file with a remove button, or an inline error. */
export default function FileDropzone({ file, error, onSelect, onRemove, browseRef }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const hintId = useId();
  const errorId = useId();

  function pick(files) {
    if (files && files[0]) onSelect(files[0]);
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files);
  }

  return (
    <div className="field">
      <span className="field__label" id={`${hintId}-label`}>
        Resume (PDF)
      </span>
      {file && !error ? (
        <div className="file-chip">
          <Icon name="file" size={22} />
          <div className="file-chip__text">
            <span className="file-chip__name" title={file.name}>
              {file.name}
            </span>
            <span className="file-chip__size">{formatBytes(file.size)}</span>
          </div>
          <button type="button" className="btn btn--ghost btn--small" onClick={onRemove}>
            <Icon name="cross" size={16} />
            Remove<span className="visually-hidden"> {file.name}</span>
          </button>
        </div>
      ) : (
        <div
          className={`dropzone${dragging ? ' dropzone--active' : ''}${error ? ' dropzone--error' : ''}`}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          data-testid="dropzone"
        >
          <Icon name="upload" size={28} />
          <p className="dropzone__text">Drag and drop your resume here, or</p>
          <button
            type="button"
            className="btn btn--secondary"
            ref={browseRef}
            onClick={() => inputRef.current?.click()}
            aria-describedby={`${hintId} ${error ? errorId : ''}`}
          >
            Browse files
          </button>
          <p className="dropzone__hint" id={hintId}>
            PDF only, up to {MAX_UPLOAD_MB} MB
          </p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="visually-hidden"
            tabIndex={-1}
            aria-labelledby={`${hintId}-label`}
            onChange={(event) => {
              pick(event.target.files);
              event.target.value = '';
            }}
            data-testid="file-input"
          />
        </div>
      )}
      {error && (
        <p className="field__error" id={errorId} role="alert">
          <Icon name="warn" size={16} /> {error}
        </p>
      )}
    </div>
  );
}
