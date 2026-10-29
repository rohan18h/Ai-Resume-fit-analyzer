// How it works (Section 13.3, page 2): the pipeline, TF-IDF vs embeddings, and the architecture diagram.
const STEPS = [
  { title: 'Upload', text: 'You upload a PDF resume and paste the job description into the web form.' },
  {
    title: 'Extract & clean',
    text: 'pdfplumber pulls the text from the PDF; it is lowercased and stripped of symbols, and names, emails and phone numbers are removed.',
  },
  {
    title: 'Identify skills',
    text: 'spaCy finds skills and key terms in both texts, using our list of 130+ skills and their aliases from SQLite.',
  },
  {
    title: 'Convert text to vectors',
    text: 'scikit-learn TF-IDF (with NLTK stopwords removed) and a sentence-embedding model turn both texts into numbers.',
  },
  {
    title: 'Compute match score',
    text: 'The fit score adds up points from five categories: required skills (35), skills shown in experience or projects (25), job duties matched by your bullets (20), degree, years and certifications (10) and ATS formatting (10). TF-IDF and embedding cosine scores are shown alongside for comparison.',
  },
  {
    title: 'Analyze gap & show results',
    text: 'Missing skills are mapped to free learning resources; the score, charts and ATS flags come back through FastAPI.',
  },
];

export default function HowItWorks() {
  return (
    <section className="page">
      <h1>How it works</h1>
      <p className="lead">
        Six steps turn your resume and a job description into a fit score, a list of missing skills and a learning
        plan. Nothing you upload is stored.
      </p>

      <h2 className="page__section-title">The pipeline</h2>
      <ol className="stepper">
        {STEPS.map((step, index) => (
          <li key={step.title} className="stepper__step">
            <span className="stepper__number" aria-hidden="true">
              {index + 1}
            </span>
            <h3 className="stepper__title">
              <span className="visually-hidden">Step {index + 1}: </span>
              {step.title}
            </h3>
            <p className="stepper__text">{step.text}</p>
          </li>
        ))}
      </ol>

      <h2 className="page__section-title">TF-IDF vs sentence embeddings</h2>
      <p>
        The app scores every resume with two methods and compares them. Both end the same way: cosine similarity
        between the resume numbers and the job description numbers gives a match percentage.
      </p>
      <div className="compare">
        <div className="card compare__card">
          <h3>TF-IDF (baseline)</h3>
          <p>
            Turns text into numbers by counting words, weighted by how special each word is. It only matches{' '}
            <strong>exact words</strong>.
          </p>
          <div className="example">
            <p className="example__pair">
              "built websites using React" vs "frontend developer experience"
            </p>
            <p className="example__result example__result--low">
              No shared words, so TF-IDF scores them as unrelated (0).
            </p>
          </div>
        </div>
        <div className="card compare__card">
          <h3>Sentence embeddings</h3>
          <p>
            A ready-made pre-trained model (all-MiniLM-L6-v2, no training) turns each sentence into numbers that capture
            its <strong>meaning</strong>.
          </p>
          <div className="example">
            <p className="example__pair">
              "built websites using React" vs "frontend developer experience"
            </p>
            <p className="example__result example__result--high">
              Similar meaning, so they score clearly closer (0.27) than "built websites using React" vs "cooking
              recipes" (0.04).
            </p>
          </div>
        </div>
      </div>
      <p className="muted small">
        The embedding matcher checks each sentence of the job description against your resume, so it can also show
        which requirements are covered best and worst ("Why this score?" on the Analyzer page).
      </p>

      <h2 className="page__section-title">System architecture</h2>
      <figure className="card architecture">
        <img
          src="/architecture.jpg"
          alt="Architecture diagram. The React and Chart.js frontend sends the PDF and job description to a FastAPI backend, which validates them and runs the NLP engine: parse and clean, skills extractor, matcher (TF-IDF and sentence embeddings), gap analyzer and ATS checker, using a SQLite database of skills and learning links. The response builder returns JSON to the results view. An offline evaluation compares both methods on hand-labelled pairs."
          loading="lazy"
        />
        <figcaption className="muted small">
          The request goes left to right and the results come back right to left. Hosting: Vercel (frontend) and Render
          (backend), with Git and GitHub for version control.
        </figcaption>
      </figure>
    </section>
  );
}
