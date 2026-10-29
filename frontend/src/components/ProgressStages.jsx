import Icon from './Icon.jsx';

export const STAGES = ['Reading your resume', 'Finding skills', 'Matching with the job', 'Checking ATS format'];

/** Loading panel: four stages in order; `current` is the active stage index. */
export default function ProgressStages({ current, slow }) {
  return (
    <div className="progress" role="status" aria-live="polite">
      <ol className="progress__stages">
        {STAGES.map((stage, index) => {
          const state = index < current ? 'done' : index === current ? 'active' : 'todo';
          return (
            <li key={stage} className={`progress__stage progress__stage--${state}`}>
              <span className="progress__marker" aria-hidden="true">
                {state === 'done' ? <Icon name="check" size={14} /> : index + 1}
              </span>
              {stage}
              {state === 'active' && <span className="visually-hidden"> (in progress)</span>}
              {state === 'done' && <span className="visually-hidden"> (done)</span>}
            </li>
          );
        })}
      </ol>
      {slow && <p className="progress__slow">The server is waking up. The first request can take up to a minute.</p>}
    </div>
  );
}
