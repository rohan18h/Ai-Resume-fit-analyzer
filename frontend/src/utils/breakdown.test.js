import { describe, expect, it } from 'vitest';
import { formatPoints, pointsAddUp, QUALIFICATION_STATUS, skillGroups } from './breakdown.js';

const skill = (name, requirement, status, extra = {}) => ({
  name,
  display_name: name,
  importance: requirement === 'preferred' ? 'low' : 'high',
  requirement,
  status,
  ...extra,
});

describe('skillGroups', () => {
  it('splits skills by requirement and evidence, dropping empty groups', () => {
    const groups = skillGroups([
      skill('Python', 'required', 'demonstrated'),
      skill('Git', 'required', 'listed'),
      skill('SQL', 'required', 'related', { via: 'PostgreSQL' }),
      skill('Django', 'required', 'missing'),
      skill('Redis', 'preferred', 'listed'),
    ]);
    expect(groups.map((g) => [g.key, g.items.map((s) => s.name)])).toEqual([
      ['shown', ['Python']],
      ['listed', ['Git']],
      ['related', ['SQL']],
      ['missing', ['Django']],
      ['preferred', ['Redis']],
    ]);
  });

  it('returns nothing for a JD without known skills', () => {
    expect(skillGroups([])).toEqual([]);
  });
});

describe('formatting', () => {
  it('shows one decimal only when needed', () => {
    expect(formatPoints(35)).toBe('35');
    expect(formatPoints(12.5)).toBe('12.5');
  });

  it('maps every qualification status to a badge', () => {
    for (const status of ['met', 'in_progress', 'unverified', 'not_met']) {
      expect(['pass', 'warn', 'fail']).toContain(QUALIFICATION_STATUS[status].badge);
    }
  });

  it('checks that category points add up to the total', () => {
    const categories = [{ points: 33.8 }, { points: 24.1 }, { points: 20 }, { points: 10 }, { points: 10 }];
    expect(pointsAddUp({ score: 97.9, categories })).toBe(true);
    expect(pointsAddUp({ score: 99, categories })).toBe(false);
  });
});
