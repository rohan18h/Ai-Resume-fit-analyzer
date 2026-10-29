import { useId } from 'react';
import Icon from './Icon.jsx';
import { percent } from '../utils/format.js';

// One-sentence explanations from Section 7.1 of the spec.
export const METHOD_INFO = {
  tfidf: {
    name: 'TF-IDF',
    text: 'Counts matching words, weighted by how special each word is, so it only rewards the exact same words.',
  },
  embeddings: {
    name: 'Embeddings',
    text: 'A pre-trained model turns sentences into numbers that capture their meaning, so different words with the same meaning still match.',
  },
};

function MethodChip({ method, score, primary }) {
  const tipId = useId();
  const info = METHOD_INFO[method];
  return (
    <span className={`chip chip--method${primary ? ' chip--primary' : ''}`}>
      {info.name} {score === null ? 'n/a' : `${percent(score)}%`}
      {primary && <span className="chip__tag">main score</span>}
      <span className="tip">
        <button type="button" className="tip__button" aria-describedby={tipId} aria-label={`About ${info.name}`}>
          <Icon name="info" size={15} />
        </button>
        <span role="tooltip" id={tipId} className="tip__bubble">
          {info.text}
        </span>
      </span>
    </span>
  );
}

/** "TF-IDF 41%" and "Embeddings 72%" chips with info tooltips; the primary method is marked. */
export default function MethodChips({ fit }) {
  return (
    <div className="method-chips">
      <MethodChip method="tfidf" score={fit.tfidf_score} primary={fit.primary_method === 'tfidf'} />
      <MethodChip method="embeddings" score={fit.embedding_score} primary={fit.primary_method === 'embeddings'} />
    </div>
  );
}
