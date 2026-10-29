import { IMPORTANCE_LABEL } from './format.js';

/** Plain-text version of the learning roadmap for "Copy roadmap as text". */
export function roadmapText(missing, done = {}) {
  if (!missing.length) return 'Learning roadmap: no missing skills found from our skills list.';
  const lines = ['Learning roadmap', ''];
  missing.forEach((skill, index) => {
    const status = done[skill.name] ? ' (done)' : '';
    lines.push(`${index + 1}. ${skill.display_name} - ${IMPORTANCE_LABEL[skill.importance]} importance${status}`);
    lines.push(`   Mentioned ${skill.mentions} time${skill.mentions === 1 ? '' : 's'} in the job description`);
    skill.resources.forEach((r) => lines.push(`   - ${r.title} (${r.provider}, ${r.level}): ${r.url}`));
    lines.push('');
  });
  return lines.join('\n').trim();
}
