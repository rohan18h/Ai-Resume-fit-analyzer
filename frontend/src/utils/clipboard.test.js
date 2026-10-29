import { describe, expect, it, vi } from 'vitest';
import { copyText } from './clipboard.js';

function fakeDoc(execResult) {
  const body = { appendChild: vi.fn(), removeChild: vi.fn() };
  const area = { style: {}, setAttribute: vi.fn(), select: vi.fn() };
  return {
    body,
    area,
    createElement: () => area,
    execCommand: vi.fn(() => {
      if (execResult instanceof Error) throw execResult;
      return execResult;
    }),
  };
}

describe('copyText', () => {
  it('uses the Clipboard API when it works', async () => {
    const clipboard = { writeText: vi.fn().mockResolvedValue(undefined) };
    const doc = fakeDoc(true);
    expect(await copyText('hi', { clipboard, doc })).toBe(true);
    expect(clipboard.writeText).toHaveBeenCalledWith('hi');
    expect(doc.execCommand).not.toHaveBeenCalled();
  });

  it('falls back to execCommand when the Clipboard API is blocked', async () => {
    const clipboard = { writeText: vi.fn().mockRejectedValue(new Error('NotAllowedError')) };
    const doc = fakeDoc(true);
    expect(await copyText('roadmap', { clipboard, doc })).toBe(true);
    expect(doc.area.value).toBe('roadmap');
    expect(doc.execCommand).toHaveBeenCalledWith('copy');
    expect(doc.body.removeChild).toHaveBeenCalledWith(doc.area); // the hidden textarea is cleaned up
  });

  it('reports failure when both routes fail', async () => {
    expect(await copyText('x', { clipboard: undefined, doc: fakeDoc(false) })).toBe(false);
    expect(await copyText('x', { clipboard: undefined, doc: fakeDoc(new Error('nope')) })).toBe(false);
    expect(await copyText('x', { clipboard: undefined, doc: undefined })).toBe(false);
  });
});
