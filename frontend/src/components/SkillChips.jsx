import Icon from './Icon.jsx';
import { IMPORTANCE_LABEL } from '../utils/format.js';

/** Matched skills (green, check icon) or missing skills (coral, with an importance badge). */
export default function SkillChips({ skills, variant }) {
  const matched = variant === 'matched';
  return (
    <ul className="skill-chips" aria-label={matched ? 'Matched skills' : 'Missing skills'}>
      {skills.map((skill) => (
        <li key={skill.name} className={`chip chip--${variant}`}>
          <Icon name={matched ? 'check' : 'cross'} size={14} />
          <span className="visually-hidden">{matched ? 'Matched: ' : 'Missing: '}</span>
          {skill.display_name}
          {!matched && (
            <span className={`badge badge--${skill.importance}`}>{IMPORTANCE_LABEL[skill.importance]}</span>
          )}
        </li>
      ))}
    </ul>
  );
}
