# Demo script (Section 18)

About 8 minutes. Files are in `backend/tests/fixtures/`; copy them to the demo laptop or phone first.

## Before you start (2 minutes before)

1. Open `https://<your-service>.onrender.com/api/health` and wait until it shows `"model_loaded": true`. A sleeping
   free instance can take up to a minute to wake up.
2. Open the app (the Vercel URL) in a second tab.

## 1. Analyzer: the main result

1. Drag `sample_resume_backend.pdf` onto the upload area (or use **Browse files**).
2. Click the **Backend Developer** sample chip, then **Analyze**.
3. Point out:
   - the **fit score** gauge and its label;
   - the two method chips, **TF-IDF** and **Embeddings**, and the info tooltips (embeddings is the main score);
   - **Skills**: "You match N of M required skills", matched (green) and missing (coral, with High / Medium / Low);
   - the **category radar** and the **method comparison** chart;
   - the **learning roadmap**: free links for each missing skill, beginner first, and **Mark as done**.

## 2. ATS check with a deliberately bad resume

1. Click **Analyze another resume**, upload `ats_bad_resume.pdf` (two columns, a table, icons, star ratings) and
   analyze it against the same sample job.
2. Open the **ATS check** card: 3 of 10 checks pass. Expand **Single-column layout**, **No tables** and
   **Few unusual symbols** to show the detail and the fix for each.
3. For contrast, `ats_good_resume.pdf` passes all 10 checks.

## 3. Why this score?

Back on the first result, scroll to **Why this score?**: the job-description lines the resume covers best and
worst, each next to the closest resume text and a similarity bar. This is the "explains the score" point from the
literature review.

## 4. Evaluation page

Open **Evaluation**: TF-IDF vs embeddings agreement with the hand labels, against the 70% target, plus the table of
every pair and both confusion matrices. Read the honesty note at the bottom.

> Until the team labels the pairs in `backend/eval/pairs.json` and reruns `python eval/evaluate.py`, this page shows
> the scores but "Not evaluated yet" for agreement. Label the pairs before the review.

## 5. How it works

Open **How it works**: the six pipeline steps, the "built websites using React" vs "frontend developer experience"
example, and the architecture diagram.

## If something goes wrong

| Problem | What to do |
| --- | --- |
| "The server is waking up..." | Wait; the first request after sleep can take up to a minute. |
| "Can't reach the server." | Check the Render dashboard; open `/api/health` directly. |
| Upload rejected | Use one of the fixture PDFs above; scanned PDFs cannot be read (by design). |
| No internet at the venue | Run both parts locally (see README) and use `http://localhost:5173`. |
