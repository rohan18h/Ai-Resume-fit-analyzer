import { describe, expect, it } from 'vitest';
import { toApiError } from './api.js';

describe('toApiError', () => {
  it('maps server error codes to friendly text', () => {
    const err = { response: { status: 422, data: { error: { code: 'unreadable_pdf', message: 'raw' } } } };
    expect(toApiError(err)).toEqual({
      code: 'unreadable_pdf',
      message: expect.stringContaining('Export it as a text PDF from Word or Google Docs'),
    });
  });

  it('covers every backend error code', () => {
    for (const code of ['invalid_file_type', 'file_too_large', 'jd_too_short', 'jd_too_long', 'unreadable_pdf',
      'too_many_pages', 'internal_error', 'invalid_request', 'no_report']) {
      const message = toApiError({ response: { data: { error: { code, message: 'raw server text' } } } }).message;
      expect(message).not.toBe('raw server text');
    }
  });

  it('falls back to the server message for unknown codes', () => {
    expect(toApiError({ response: { data: { error: { code: 'new_code', message: 'Server says hi' } } } }).message).toBe(
      'Server says hi',
    );
  });

  it('handles network failures and timeouts', () => {
    expect(toApiError({ request: {} })).toEqual({ code: 'network_error', message: "Can't reach the server." });
    expect(toApiError({ code: 'ECONNABORTED' }).code).toBe('timeout');
    expect(toApiError({ response: { status: 502, data: '<html>' } }).code).toBe('internal_error');
  });
});
