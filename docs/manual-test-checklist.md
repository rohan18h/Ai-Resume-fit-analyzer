# Frontend manual test checklist (Section 14)

Run against the local backend (`uvicorn app.main:app --port 8000`) and frontend (`npm run dev`).
Test files are in `backend/tests/fixtures/`.

Last run: Step 11, 2026-10-29, in the Claude desktop app's built-in Chromium browser. "Automated" means the
check was driven by scripted clicks, key presses and file drops in that browser, not by a person.
**The items marked "Needs a person" have not been done yet.** Tick them off before the review.

| # | Check | How | Result |
| --- | --- | --- | --- |
| 1 | Upload with the Browse button and the system file dialog | Needs a person | Not done: the OS file dialog cannot be driven from the test browser |
| 2 | Drag and drop a PDF | Automated (real `drop` event with a PDF file) | Pass |
| 3 | Wrong file type | Automated: `.docx` file | Pass: inline "Please choose a PDF file." |
| 4 | File over 5 MB | Automated: 6 MB file | Pass: inline "The file is larger than 5 MB." |
| 5 | Long file name | Automated: 60-character name | Pass: cut off with "...", full name on hover |
| 6 | Empty / too short / too long job description | Automated | Pass: Analyze disabled with the reason shown; counter turns red |
| 7 | Sample chips | Automated (mouse and keyboard) | Pass: all three fill the textarea |
| 8 | Loading stages | Automated | Pass: four stages advance on a timer |
| 9 | Slow server notice after 8 s | Automated: requests delayed by 9 s in the page | Pass: "The server is waking up..." appears, results arrive afterwards |
| 10 | Error banner: not a PDF (`corrupt.pdf`) | Automated | Pass: friendly message + Try again |
| 11 | Error banner: scanned / blank / truncated PDF | Automated | Pass: "We couldn't read text from this PDF..." |
| 12 | Error banner: more than 5 pages (`six_pages.pdf`) | Automated | Pass |
| 13 | Error banner: server not reachable | Automated: backend stopped | Pass: "Can't reach the server." |
| 14 | Error banner: `file_too_large`, `jd_too_short`, `jd_too_long`, `internal_error`, timeout from the server | Backend tests + `api.test.js` (the UI blocks these inputs before sending) | Pass |
| 15 | Results: every section shows | Automated with `sample_resume_backend.pdf` + Backend Developer sample | Pass |
| 16 | Copy roadmap as text | Automated real mouse click | Pass ("Roadmap copied") using the fallback copy method; the test browser blocks the newer Clipboard API |
| 17 | Mark as done is remembered | Automated (mouse and Space key) | Pass: saved in this browser's localStorage |
| 18 | Print / Save as PDF | Print rules applied to the screen and checked | Pass: inputs, nav and buttons hidden; results, roadmap and link addresses shown. **Needs a person:** open the real print preview once |
| 19 | Mobile width 375 px | Automated: emulated 375 x 812 | Pass: no sideways scroll on any page, sections stack, wide tables scroll in their own box |
| 20 | Keyboard-only use | Automated real Tab / Enter / Space presses | Pass: logical order, visible focus ring on every stop, chips, Analyze, info tips, roadmap links and checkboxes, ATS rows and action buttons all work; focus moves to "Your results" |
| 21 | Accessibility audit (axe-core 4.14, WCAG 2.1 A + AA) | Automated on Analyzer (inputs and results), Evaluation, How it works, About | Pass: 0 violations after fixing green-on-green contrast and chart text alternatives |
| 22 | Screen reader spot check | Needs a person (NVDA on Windows is free) | Not done |
| 23 | Real phone | Needs a person (after deployment, Step 12) | Not done |

## Performance (Objective 5)

`backend/tests/test_performance.py`: 2-page resume (`two_page_resume.pdf`) and a 450-word job description,
after warm-up. Last run: 0.26 to 0.39 s per request end to end (limit 5 s). In the browser the full flow took
about 0.4 s.

## Known behaviour

- If a new analysis fails, the previous results stay on the page under the error banner until a new analysis
  succeeds.
- The Analyze button is skipped by Tab while it is disabled; the reason is shown as text next to it.
