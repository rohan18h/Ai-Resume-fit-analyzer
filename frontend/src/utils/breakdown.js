// Shapes the weighted score's breakdown (response.breakdown) for the Score breakdown section.

/** Skill groups shown as chip rows, in order. Empty groups are dropped. */
export function skillGroups(skills) {
  const pick = (requirement, ...statuses) =>
    skills.filter((s) => s.requirement === requirement && statuses.includes(s.status));
  return [
    { key: 'shown', title: 'Required skills shown in your experience or projects', variant: 'matched', items: pick('required', 'demonstrated') },
    { key: 'listed', title: 'Required skills only listed (not shown in a bullet)', variant: 'partial', items: pick('required', 'listed') },
    { key: 'related', title: 'Required skills covered only by a related skill', variant: 'partial', items: pick('required', 'related') },
    { key: 'missing', title: 'Missing required skills', variant: 'missing', items: pick('required', 'missing') },
    { key: 'preferred', title: 'Preferred skills you have', variant: 'matched', items: pick('preferred', 'demonstrated', 'listed') },
    { key: 'preferred-missing', title: 'Preferred skills not found', variant: 'missing', items: pick('preferred', 'related', 'missing') },
  ].filter((group) => group.items.length > 0);
}

/** Qualification status -> pass / warn / fail badge plus a word, so colour is never the only signal. */
export const QUALIFICATION_STATUS = {
  met: { badge: 'pass', text: 'Met' },
  in_progress: { badge: 'warn', text: 'In progress' },
  unverified: { badge: 'warn', text: 'Not found' },
  not_met: { badge: 'fail', text: 'Not met' },
};

/** "12.5" -> "12.5", 12 -> "12": one decimal only when needed. */
export function formatPoints(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/** True when the shown category points add up to the total (they always should). */
export function pointsAddUp(breakdown) {
  const sum = breakdown.categories.reduce((total, c) => total + c.points, 0);
  return Math.abs(Math.round(sum * 10) / 10 - breakdown.score) < 0.05;
}
