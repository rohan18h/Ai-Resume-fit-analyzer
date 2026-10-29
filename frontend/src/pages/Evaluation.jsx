import { useEffect, useState } from 'react';
import { getEvaluation, toApiError } from '../api.js';
import AgreementChart from '../components/AgreementChart.jsx';
import ConfusionMatrix from '../components/ConfusionMatrix.jsx';
import EvalSummary from '../components/EvalSummary.jsx';
import Icon from '../components/Icon.jsx';
import { isCorrect, METHODS, summarize } from '../utils/evaluation.js';

function Verdict({ correct }) {
  if (correct === null) return null;
  return correct ? (
    <span className="verdict verdict--right">
      <Icon name="check" size={14} /> <span className="visually-hidden">correct</span>
    </span>
  ) : (
    <span className="verdict verdict--wrong">
      <Icon name="cross" size={14} /> <span className="visually-hidden">wrong</span>
    </span>
  );
}

// Evaluation (Section 13.3, page 3): TF-IDF vs embeddings on the hand-labelled pairs, from GET /api/evaluation.
export default function Evaluation() {
  const [state, setState] = useState({ status: 'loading' });

  useEffect(() => {
    let active = true;
    getEvaluation()
      .then((report) => active && setState({ status: 'ok', report }))
      .catch((err) => active && setState({ status: 'error', error: toApiError(err) }));
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="page">
      <h1>Evaluation</h1>
      <p className="lead">
        Do the two matching methods agree with how people judge a resume? Both are run on the same hand-labelled
        resume-job pairs and compared with the labels (Objectives 2 and 3).
      </p>
      <div aria-live="polite">
        {state.status === 'loading' && <p className="muted">Loading the evaluation report...</p>}
        {state.status === 'error' && (
          <p className="banner banner--warn">
            <Icon name="info" size={18} />
            {state.error.code === 'no_report' ? 'Evaluation has not been run yet.' : state.error.message}
          </p>
        )}
      </div>
      {state.status === 'ok' && <Report report={state.report} />}
    </section>
  );
}

function Report({ report }) {
  const summary = summarize(report);
  const labelled = summary.labelled > 0;
  const generated = new Date(report.generated_at).toLocaleString();

  return (
    <>
      <EvalSummary summary={summary} />

      {!labelled && (
        <p className="banner banner--warn">
          <Icon name="info" size={18} />
          <span>
            No pair has a hand label yet, so agreement cannot be calculated. The scores below are real; the team adds
            the labels in <code>backend/eval/pairs.json</code> and reruns the evaluation.
          </span>
        </p>
      )}

      {labelled && summary.tfidf && summary.embeddings && (
        <section className="card result">
          <h2 className="result__title">Agreement with hand labels</h2>
          <AgreementChart
            tfidf={summary.tfidf.agreement_percent}
            embeddings={summary.embeddings.agreement_percent}
            target={summary.target}
          />
          <p className="muted small">
            Spearman correlation between score and label: TF-IDF {summary.tfidf.spearman ?? 'n/a'}, embeddings{' '}
            {summary.embeddings.spearman ?? 'n/a'}.
          </p>
        </section>
      )}

      <section className="card result">
        <h2 className="result__title">Every pair</h2>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Scores for every pair">
          <table className="eval-table">
            <thead>
              <tr>
                <th scope="col">Pair</th>
                <th scope="col">Hand label</th>
                {METHODS.map((m) => (
                  <th key={m.key} scope="col">
                    {m.name} score (predicted)
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <tr key={row.id}>
                  <th scope="row">{row.id}</th>
                  <td>{row.label ?? <span className="muted">not labelled</span>}</td>
                  {METHODS.map((m) =>
                    row[`${m.key}_score`] === undefined ? (
                      <td key={m.key} className="muted">
                        n/a
                      </td>
                    ) : (
                      <td key={m.key}>
                        {row[`${m.key}_score`].toFixed(1)} ({row[`${m.key}_pred`]}){' '}
                        <Verdict correct={isCorrect(row, m.key)} />
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {labelled && (
        <section className="card result">
          <h2 className="result__title">Confusion matrices</h2>
          <div className="matrices">
            {METHODS.map(
              (m) =>
                summary[m.key] && (
                  <ConfusionMatrix
                    key={m.key}
                    title={m.name}
                    matrix={summary[m.key].confusion}
                    labels={summary.labelOrder}
                  />
                ),
            )}
          </div>
        </section>
      )}

      <footer className="eval-notes">
        <h2 className="result__title">Notes</h2>
        <ul>
          {report.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
          <li>
            With a small dataset, tuning the thresholds on the same pairs makes results look better than they are, so
            results are reported with the default thresholds first (good &ge; {report.thresholds.good_min}, average
            &ge; {report.thresholds.average_min}). If embeddings do not beat TF-IDF, that is reported too.
          </li>
        </ul>
        <p className="muted small">Report generated {generated}.</p>
      </footer>
    </>
  );
}
