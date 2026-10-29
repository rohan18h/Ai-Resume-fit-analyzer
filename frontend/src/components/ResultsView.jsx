import { forwardRef, useState } from 'react';
import AtsPanel from './AtsPanel.jsx';
import CategoryRadar from './CategoryRadar.jsx';
import CoverageBar from './CoverageBar.jsx';
import ExplanationPanel from './ExplanationPanel.jsx';
import Icon from './Icon.jsx';
import MethodBarChart from './MethodBarChart.jsx';
import MethodChips from './MethodChips.jsx';
import RoadmapCard from './RoadmapCard.jsx';
import ScoreGauge from './ScoreGauge.jsx';
import SkillChips from './SkillChips.jsx';
import { scoreColor } from './charts.js';
import { formatSeconds } from '../utils/format.js';
import { roadmapText } from '../utils/roadmap.js';
import { loadDone, saveDone } from '../utils/storage.js';

function Section({ title, children, className = '' }) {
  return (
    <section className={`card result ${className}`}>
      <h3 className="result__title">{title}</h3>
      {children}
    </section>
  );
}

function Roadmap({ missing, jdHasSkills }) {
  const [done, setDone] = useState(loadDone);
  const [copyStatus, setCopyStatus] = useState('');

  function toggle(name) {
    const next = { ...done, [name]: !done[name] };
    setDone(next);
    saveDone(next);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(roadmapText(missing, done));
      setCopyStatus('Roadmap copied to the clipboard.');
    } catch {
      setCopyStatus('Copying is blocked in this browser. Select the text and copy it instead.');
    }
  }

  if (!jdHasSkills) {
    return <p className="muted">No roadmap: the job description has no skills from our list to compare with.</p>;
  }
  if (!missing.length) {
    return <p className="celebrate">No missing skills found from our skills list.</p>;
  }
  return (
    <>
      <div className="toolbar no-print">
        <button type="button" className="btn btn--secondary btn--small" onClick={copy}>
          <Icon name="copy" size={16} /> Copy roadmap as text
        </button>
        <button type="button" className="btn btn--secondary btn--small" onClick={() => window.print()}>
          <Icon name="print" size={16} /> Print / Save as PDF
        </button>
        <span className="toolbar__status" aria-live="polite">
          {copyStatus}
        </span>
      </div>
      <ul className="roadmap">
        {missing.map((skill) => (
          <RoadmapCard key={skill.name} skill={skill} done={Boolean(done[skill.name])} onToggle={() => toggle(skill.name)} />
        ))}
      </ul>
    </>
  );
}

/** Every result section from Section 13.3, in order. */
const ResultsView = forwardRef(function ResultsView({ result, onAnalyzeAnother, onEditJd }, headingRef) {
  const { fit, skills, explanation, ats, warnings } = result;
  const totalSkills = skills.matched.length + skills.missing.length;

  return (
    <div className="results" aria-labelledby="results-heading">
      <h2 id="results-heading" ref={headingRef} tabIndex={-1} className="results__heading">
        Your results
      </h2>

      {warnings.length > 0 && (
        <ul className="notices">
          {warnings.map((warning) => (
            <li key={warning} className="banner banner--warn">
              <Icon name="warn" size={18} />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="results__grid">
        <Section title="Fit summary" className="result--fit">
          <div className="fit">
            <ScoreGauge
              score={fit.score}
              caption={fit.label}
              color={scoreColor(fit.score)}
              label={`Fit score ${Math.round(fit.score)} percent, ${fit.label}`}
            />
            <div className="fit__side">
              <MethodChips fit={fit} />
              <p className="muted small">Analyzed in {formatSeconds(result.processing_ms)}</p>
            </div>
          </div>
        </Section>

        <Section title="Skills" className="result--skills">
          {totalSkills === 0 ? (
            <p className="banner banner--warn">
              <Icon name="warn" size={18} /> No known skills were found in the job description. It may be too short or
              use skills outside our list.
            </p>
          ) : (
            <>
              <CoverageBar matched={skills.matched.length} total={totalSkills} percentValue={skills.coverage_percent} />
              <h4 className="subheading">Matched</h4>
              {skills.matched.length ? (
                <SkillChips skills={skills.matched} variant="matched" />
              ) : (
                <p className="muted small">None of the job description's skills were found in your resume.</p>
              )}
              <h4 className="subheading">Missing</h4>
              {skills.missing.length ? (
                <SkillChips skills={skills.missing} variant="missing" />
              ) : (
                <p className="celebrate">No missing skills found from our skills list.</p>
              )}
            </>
          )}
        </Section>

        {skills.by_category.length > 0 && (
          <Section title="Skill coverage by category">
            <CategoryRadar byCategory={skills.by_category} />
          </Section>
        )}

        <Section title="Method comparison">
          <MethodBarChart fit={fit} />
        </Section>
      </div>

      <Section title="Learning roadmap" className="result--roadmap">
        <Roadmap missing={skills.missing} jdHasSkills={totalSkills > 0} />
      </Section>

      <div className="results__grid">
        <Section title="ATS check">
          <AtsPanel ats={ats} />
        </Section>

        {explanation && (
          <Section title="Why this score?">
            <ExplanationPanel explanation={explanation} />
          </Section>
        )}
      </div>

      <div className="actions no-print">
        <button type="button" className="btn btn--primary" onClick={onAnalyzeAnother}>
          Analyze another resume
        </button>
        <button type="button" className="btn btn--secondary" onClick={onEditJd}>
          <Icon name="edit" size={16} /> Edit job description and re-run
        </button>
      </div>
    </div>
  );
});

export default ResultsView;
