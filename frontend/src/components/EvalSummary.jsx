import Icon from './Icon.jsx';
import { formatPercent } from '../utils/evaluation.js';

/** Summary tiles: pairs, TF-IDF agreement, embeddings agreement, and whether the 70% target is met. */
export default function EvalSummary({ summary }) {
  const { met, target } = summary;
  const verdict =
    met === null
      ? { className: 'tile--pending', icon: 'info', text: 'Not evaluated yet' }
      : met
        ? { className: 'tile--met', icon: 'check', text: 'Target met' }
        : { className: 'tile--missed', icon: 'cross', text: 'Target not met' };

  return (
    <ul className="tiles">
      <li className="tile">
        <span className="tile__value">{summary.pairs}</span>
        <span className="tile__label">resume-job pairs ({summary.labelled} with hand labels)</span>
      </li>
      <li className="tile">
        <span className="tile__value">{formatPercent(summary.tfidf?.agreement_percent)}</span>
        <span className="tile__label">TF-IDF agreement with hand labels</span>
      </li>
      <li className="tile">
        <span className="tile__value">{formatPercent(summary.embeddings?.agreement_percent)}</span>
        <span className="tile__label">Embeddings agreement with hand labels</span>
      </li>
      <li className={`tile ${verdict.className}`}>
        <span className="tile__value tile__value--verdict">
          <Icon name={verdict.icon} size={22} /> {verdict.text}
        </span>
        <span className="tile__label">Objective 3: embeddings agree on at least {target}% of pairs</span>
      </li>
    </ul>
  );
}
