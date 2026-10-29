import { useEffect, useState } from 'react';
import { getHealth, toApiError } from '../api.js';

// Step 0: page shell plus a backend connection check. The full analyzer is built in Step 9.
export default function Analyzer() {
  const [status, setStatus] = useState({ state: 'loading' });

  useEffect(() => {
    let active = true;
    getHealth()
      .then((data) => active && setStatus({ state: 'ok', data }))
      .catch((err) => active && setStatus({ state: 'error', error: toApiError(err) }));
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1>Know your fit before you apply.</h1>
      <p className="lead">
        Upload your resume, paste a job description, and see your fit score, missing skills and a plan to close the
        gap.
      </p>

      <div className="card">
        <h2>Backend connection</h2>
        <p role="status" aria-live="polite" className={`status status--${status.state}`}>
          {status.state === 'loading' && 'Checking the server…'}
          {status.state === 'ok' &&
            `✓ Connected: status "${status.data.status}", version ${status.data.version}, model loaded: ${
              status.data.model_loaded ? 'yes' : 'no'
            }`}
          {status.state === 'error' && `✗ ${status.error.message}`}
        </p>
      </div>

      <p className="muted">Your resume is processed in memory and never stored.</p>
    </section>
  );
}
