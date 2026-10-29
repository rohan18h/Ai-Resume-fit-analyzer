import { SAMPLE_JOBS } from '../data/sampleJobs.js';

/** "Try a sample" chips that fill the job description textarea. */
export default function SampleChips({ onPick }) {
  return (
    <div className="sample-chips" role="group" aria-label="Try a sample job description">
      <span className="sample-chips__label">Try a sample:</span>
      {SAMPLE_JOBS.map((job) => (
        <button key={job.id} type="button" className="chip chip--button" onClick={() => onPick(job.text)}>
          {job.label}
        </button>
      ))}
    </div>
  );
}
