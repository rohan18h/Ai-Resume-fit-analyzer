// Input rules shown in the UI. They mirror the backend defaults in backend/app/config.py.
export const MAX_UPLOAD_MB = 5;
export const MIN_JD_CHARS = 50;
export const MAX_JD_CHARS = 10000;

/** Returns an error message for a picked file, or null if it is acceptable. */
export function fileProblem(file) {
  if (!file) return null;
  const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name || '');
  if (!isPdf) return 'Please choose a PDF file.';
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `The file is larger than ${MAX_UPLOAD_MB} MB.`;
  if (file.size === 0) return 'The file is empty.';
  return null;
}

/** Returns a message if the job description is too short or too long, or null if it is fine. */
export function jdProblem(text) {
  const length = (text || '').trim().length;
  if (length < MIN_JD_CHARS) return `Add at least ${MIN_JD_CHARS} characters of job description (${length} so far).`;
  if (length > MAX_JD_CHARS) return `Shorten the job description to ${MAX_JD_CHARS.toLocaleString()} characters.`;
  return null;
}

/** Why the Analyze button is disabled, or null when both inputs are valid. */
export function analyzeBlockReason(file, jd) {
  if (!file) return 'Upload your resume as a PDF.';
  const problem = fileProblem(file);
  if (problem) return problem;
  return jdProblem(jd);
}
