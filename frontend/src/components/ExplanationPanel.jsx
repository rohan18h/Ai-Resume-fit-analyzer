function SimilarityBar({ value }) {
  const pct = Math.round(value * 100);
  return (
    <div className="similarity">
      <div className="bar bar--thin" role="presentation">
        <div className="bar__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="similarity__value">{pct}% similar</span>
    </div>
  );
}

function MatchList({ title, items, resumeKey, empty }) {
  return (
    <div className="explain__column">
      <h4>{title}</h4>
      {items.length === 0 ? (
        <p className="muted small">{empty}</p>
      ) : (
        <ol className="explain__list">
          {items.map((item, index) => (
            <li key={index} className="explain__item">
              <div className="explain__pair">
                <div>
                  <span className="explain__source">Job description</span>
                  <p className="explain__snippet">{item.jd_snippet}</p>
                </div>
                <div>
                  <span className="explain__source">Closest part of your resume</span>
                  <p className="explain__snippet">{item[resumeKey]}</p>
                </div>
              </div>
              <SimilarityBar value={item.similarity} />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/** "Why this score?": job description parts that the resume covers best and worst. */
export default function ExplanationPanel({ explanation }) {
  return (
    <div>
      <div className="explain">
        <MatchList
          title="Strongest matches"
          items={explanation.strong_matches}
          resumeKey="resume_snippet"
          empty="No strong matches found."
        />
        <MatchList
          title="Weakest spots"
          items={explanation.weak_spots}
          resumeKey="best_resume_snippet"
          empty="The job description is too short to show weak spots."
        />
      </div>
      <p className="muted small">
        Weak spots are parts of the job description that nothing in your resume covers well.
      </p>
    </div>
  );
}
