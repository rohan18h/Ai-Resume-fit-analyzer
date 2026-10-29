// All API calls live here: one function per endpoint (Section 13.4).
// Error shapes are also handled here, so components only ever see { code, message }.
import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({ baseURL: `${API_BASE_URL}/api` });

// Friendly text for every error code the backend can return (Section 10.3), plus client-side ones.
const FRIENDLY_MESSAGES = {
  invalid_file_type: "This file isn't a PDF. Please upload your resume as a PDF.",
  file_too_large: 'The PDF is larger than 5 MB. Please upload a smaller file.',
  jd_too_short: 'The job description is too short. Paste at least 50 characters.',
  jd_too_long: 'The job description is too long. Keep it under 10,000 characters.',
  unreadable_pdf:
    "We couldn't read text from this PDF. It may be a scanned image. Export it as a text PDF from Word or Google Docs and try again.",
  too_many_pages: 'Your resume has more than 5 pages. Please upload a shorter version.',
  invalid_request: 'Something was missing from the request. Please check the resume and the job description.',
  internal_error: 'Something went wrong on our side. Please try again.',
  no_report: 'Evaluation has not been run yet.',
  network_error: "Can't reach the server.",
  timeout: 'The server took too long to respond. Please try again.',
};

/** Turn any axios error into { code, message } with a friendly message. */
export function toApiError(err) {
  if (err?.response?.data?.error?.code) {
    const { code, message } = err.response.data.error;
    return { code, message: FRIENDLY_MESSAGES[code] || message || FRIENDLY_MESSAGES.internal_error };
  }
  if (err?.code === 'ECONNABORTED') return { code: 'timeout', message: FRIENDLY_MESSAGES.timeout };
  if (err?.response) return { code: 'internal_error', message: FRIENDLY_MESSAGES.internal_error };
  return { code: 'network_error', message: FRIENDLY_MESSAGES.network_error };
}

export async function getHealth() {
  const { data } = await client.get('/health');
  return data;
}

/** POST /api/analyze with the resume PDF and the job description. A sleeping free server can take a minute. */
export async function analyzeResume(file, jobDescription, { method = 'both', signal } = {}) {
  const form = new FormData();
  form.append('resume', file);
  form.append('job_description', jobDescription);
  form.append('method', method);
  const { data } = await client.post('/analyze', form, { signal, timeout: 120000 });
  return data;
}
