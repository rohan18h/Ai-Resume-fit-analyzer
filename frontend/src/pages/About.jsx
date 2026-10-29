// About (Section 13.3, page 4). Content comes from Part A of the project spec (the review presentations).
const PROBLEMS = [
  "Job seekers can't tell if they're a good fit before applying.",
  "When rejected, they don't know which skills they were missing.",
  'Recruiters waste time screening resumes manually.',
  'Resumes get auto-rejected by ATS for formatting issues.',
];

const OBJECTIVES = [
  ['Extract text from PDF resume and job description', '9 of 10 test PDFs read correctly', 'Week 3'],
  ['Give a fit score (TF-IDF + cosine baseline)', 'Score for 10+ hand-labelled pairs', 'Week 5'],
  ['Add sentence embeddings and compare', '≥ 70% agreement with hand labels', 'Week 7'],
  ['List missing skills with free learning links', '100+ skills, 1+ link each', 'Week 8'],
  ['Check ATS formatting and show results in a web app', '8+ checks; result in ≤ 5 seconds', 'Week 11'],
];

const PAPERS = [
  {
    paper: 'Kaur, Gill & Gill (2025), Resume Sorting Using ML - A Review',
    did: 'Reviewed about 20 systems (SVM, KNN, BERT). Best about 96% using TF-IDF features.',
    limit: 'Only helps recruiters sort resumes. No feedback for the candidate.',
    differs: 'Tells the job seeker the missing skills and what to learn.',
  },
  {
    paper: 'Lavi et al. (2021), conSultantBERT - RecSys in HR',
    url: 'https://arxiv.org/abs/2109.06501',
    did: 'Fine-tuned SBERT on 274k labelled pairs. Beat TF-IDF (0.85 vs 0.57 AUC).',
    limit: 'Needs huge private data and a GPU. Gives a score with no reason.',
    differs: 'Ready-made model, no training. Explains the score.',
  },
  {
    paper: 'Grech & Suda (2020), Neural Résumé Search - ICPRAM',
    url: 'https://www.scitepress.org/Papers/2020/93550/',
    did: 'Word embeddings + TF-IDF + cosine on 2,000 resumes.',
    limit: 'Tested on only 3 jobs. Ignores word order and context.',
    differs: 'Context-aware embeddings + our own labelled test set.',
  },
];

const STACK = [
  ['Frontend', 'React.js, Chart.js', 'Upload form and score charts; most used UI library'],
  ['Backend', 'Python, FastAPI', 'Same language as the ML code; fast and modern'],
  ['NLP', 'pdfplumber, spaCy, NLTK', 'Read PDF text and find skills; industry standard'],
  ['Matching', 'scikit-learn, sentence-transformers', 'TF-IDF baseline + meaning-based embeddings'],
  ['Database', 'SQLite', 'Stores skills and learning links; no server needed'],
  ['Deploy & tools', 'Render, Vercel, Git + GitHub', 'Free hosting and team version control'],
];

const FUTURE = [
  'Ranking many resumes for recruiters',
  'LLM-based rewrite suggestions',
  'Resumes in other languages',
  'Browser extension',
  'User accounts and scan history',
  'OCR for scanned PDFs',
  'DOCX upload',
];

const LIMITATIONS = [
  'English only.',
  'PDF only; scanned (image) PDFs cannot be read.',
  'Skills that are not in our skills list are missed.',
  'Scores depend on the quality of the text extracted from the PDF.',
];

export default function About() {
  return (
    <section className="page">
      <h1>About</h1>
      <p className="lead">
        AI-Powered Resume Fit Analyzer: scoring resume-job fit and mapping the skill gap. A TY Computer Engineering
        mini project.
      </p>

      <div className="about-grid">
        <section className="card result">
          <h2 className="result__title">Problem</h2>
          <ul className="plain-list">
            {PROBLEMS.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>
        <section className="card result">
          <h2 className="result__title">Purpose</h2>
          <p>Show a job seeker, before applying, their fit score, missing skills and what to learn.</p>
          <h3 className="subheading">Responsible use</h3>
          <p className="small">
            The fit score is an estimate to help applicants improve. It must not be used to make hiring decisions about
            people.
          </p>
        </section>
      </div>

      <section className="card result">
        <h2 className="result__title">Objectives</h2>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Objectives">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Objective</th>
                <th scope="col">Measure</th>
                <th scope="col">By</th>
              </tr>
            </thead>
            <tbody>
              {OBJECTIVES.map(([objective, measure, week], index) => (
                <tr key={objective}>
                  <td>{index + 1}</td>
                  <td>{objective}</td>
                  <td>{measure}</td>
                  <td>{week}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card result">
        <h2 className="result__title">Literature review</h2>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Literature review">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Paper</th>
                <th scope="col">What they did</th>
                <th scope="col">Limitation</th>
                <th scope="col">How our project differs</th>
              </tr>
            </thead>
            <tbody>
              {PAPERS.map((p) => (
                <tr key={p.paper}>
                  <td>
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer">
                        {p.paper}
                        <span className="visually-hidden"> (opens in a new tab)</span>
                      </a>
                    ) : (
                      p.paper
                    )}
                  </td>
                  <td>{p.did}</td>
                  <td>{p.limit}</td>
                  <td>{p.differs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small">
          Numbers are as quoted in the team's presentation. Background on ATS problems:{' '}
          <a href="https://arxiv.org/html/2602.04087v1" target="_blank" rel="noopener noreferrer">
            Quantifying Algorithmic Friction in Automated Resume Screening Systems (arXiv, 2026)
          </a>
          .
        </p>
      </section>

      <section className="card result">
        <h2 className="result__title">Design and technology stack</h2>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Technology stack">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Layer</th>
                <th scope="col">Tool</th>
                <th scope="col">Why it fits</th>
              </tr>
            </thead>
            <tbody>
              {STACK.map(([layer, tool, why]) => (
                <tr key={layer}>
                  <td>{layer}</td>
                  <td>{tool}</td>
                  <td>{why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="about-grid">
        <section className="card result">
          <h2 className="result__title">Team</h2>
          <p>Team: [Names]</p>
          <p>Guide: [Guide name]</p>
        </section>
        <section className="card result">
          <h2 className="result__title">Limitations</h2>
          <ul className="plain-list">
            {LIMITATIONS.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="card result">
        <h2 className="result__title">Future ideas</h2>
        <ul className="skill-chips">
          {FUTURE.map((f) => (
            <li key={f} className="chip chip--method">
              {f}
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
