import { useEffect, useRef, useState } from 'react';
import { analyzeResume, toApiError } from '../api.js';
import AnalyzeButton from '../components/AnalyzeButton.jsx';
import ErrorBanner from '../components/ErrorBanner.jsx';
import FileDropzone from '../components/FileDropzone.jsx';
import Icon from '../components/Icon.jsx';
import JobDescriptionInput from '../components/JobDescriptionInput.jsx';
import ProgressStages, { STAGES } from '../components/ProgressStages.jsx';
import ResultsView from '../components/ResultsView.jsx';
import { countWords } from '../utils/format.js';
import { analyzeBlockReason, fileProblem } from '../utils/validation.js';

const STAGE_MS = 900; // advance the loading stages on a timer until the response arrives
const SLOW_MS = 8000; // after this, explain that a sleeping free server can take a minute

export default function Analyzer() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [jd, setJd] = useState('');
  const [status, setStatus] = useState('idle'); // idle | loading | done
  const [stage, setStage] = useState(0);
  const [slow, setSlow] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [collapsed, setCollapsed] = useState(false);

  const resultsHeading = useRef(null);
  const textareaRef = useRef(null);
  const browseRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    if (status !== 'loading') return undefined;
    const stageTimer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), STAGE_MS);
    const slowTimer = setTimeout(() => setSlow(true), SLOW_MS);
    return () => {
      clearInterval(stageTimer);
      clearTimeout(slowTimer);
    };
  }, [status]);

  useEffect(() => {
    if (status === 'done' && resultsHeading.current) {
      resultsHeading.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      resultsHeading.current.focus({ preventScroll: true });
    }
  }, [status]);

  function selectFile(picked) {
    setFile(picked);
    setFileError(fileProblem(picked));
  }

  function removeFile() {
    setFile(null);
    setFileError(null);
    setTimeout(() => browseRef.current?.focus(), 0);
  }

  async function analyze() {
    if (analyzeBlockReason(file, jd)) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setError(null);
    setStage(0);
    setSlow(false);
    setStatus('loading');
    try {
      const data = await analyzeResume(file, jd.trim(), { signal: controller.signal });
      setStage(STAGES.length);
      setResult(data);
      setCollapsed(true);
      setStatus('done');
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(toApiError(err));
      setStatus(result ? 'done' : 'idle');
    }
  }

  function analyzeAnother() {
    setResult(null);
    setStatus('idle');
    setCollapsed(false);
    setFile(null);
    setFileError(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => browseRef.current?.focus(), 0);
  }

  function editJd() {
    setCollapsed(false);
    setTimeout(() => {
      textareaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      textareaRef.current?.focus({ preventScroll: true });
    }, 0);
  }

  const blockReason = analyzeBlockReason(file, jd);
  const loading = status === 'loading';

  return (
    <section className="analyzer">
      <header className="analyzer__intro no-print">
        <h1>Know your fit before you apply.</h1>
        <p className="lead">
          Upload your resume, paste a job description, and see your fit score, missing skills and a plan to close the
          gap.
        </p>
      </header>

      {error && <ErrorBanner error={error} onRetry={blockReason ? null : analyze} onDismiss={() => setError(null)} />}

      {collapsed && result ? (
        <div className="summary-bar no-print">
          <Icon name="file" size={18} />
          <span className="summary-bar__text" title={file?.name}>
            {file?.name ?? 'Resume'} · Job description ({countWords(jd)} words)
          </span>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => setCollapsed(false)}>
            <Icon name="edit" size={16} /> Edit
          </button>
        </div>
      ) : (
        <div className="card input-card no-print">
          <div className="input-card__grid">
            <FileDropzone
              file={file}
              error={fileError}
              onSelect={selectFile}
              onRemove={removeFile}
              browseRef={browseRef}
            />
            <JobDescriptionInput value={jd} onChange={setJd} textareaRef={textareaRef} />
          </div>
          {loading ? (
            <ProgressStages current={stage} slow={slow} />
          ) : (
            <AnalyzeButton disabledReason={blockReason} onClick={analyze} />
          )}
          <p className="privacy">
            <Icon name="info" size={16} /> Your resume is processed in memory and never stored.
          </p>
        </div>
      )}

      {collapsed && loading && <ProgressStages current={stage} slow={slow} />}

      {result && (
        <ResultsView ref={resultsHeading} result={result} onAnalyzeAnother={analyzeAnother} onEditJd={editJd} />
      )}
    </section>
  );
}
