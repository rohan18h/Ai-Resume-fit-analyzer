// Small inline SVG icons (no icon library). Decorative by default; pass `label` when the icon carries meaning alone.
const PATHS = {
  check: 'M5 12.5l4.5 4.5L19 7.5',
  cross: 'M6 6l12 12M18 6L6 18',
  warn: 'M12 4l9 16H3L12 4zM12 10v4.5M12 17.5v.5',
  info: 'M12 3a9 9 0 100 18 9 9 0 000-18zM12 11v6M12 7.5v.5',
  upload: 'M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3',
  file: 'M7 3h7l5 5v12a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1zM14 3v5h5',
  external: 'M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5',
  docs: 'M6 4h9l3 3v13H6zM9 10h6M9 13h6M9 16h4',
  course: 'M3 9l9-4 9 4-9 4-9-4zM7 11v4c0 1.5 2.5 3 5 3s5-1.5 5-3v-4',
  video: 'M4 6h11a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1zM16 10l5-3v10l-5-3',
  tutorial: 'M5 5h14M5 10h14M5 15h9M5 20h6',
  book: 'M5 4h6a2 2 0 012 2v14a2 2 0 00-2-2H5zM19 4h-6a2 2 0 00-2 2v14a2 2 0 012-2h6z',
  copy: 'M9 9h10v11H9zM5 15V4h10',
  print: 'M7 9V4h10v5M7 17H5a1 1 0 01-1-1v-5a1 1 0 011-1h14a1 1 0 011 1v5a1 1 0 01-1 1h-2M7 14h10v6H7z',
  edit: 'M4 20h4L19 9l-4-4L4 16v4z',
};

export default function Icon({ name, size = 18, label, className = '' }) {
  return (
    <svg
      className={`icon ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

/** Icon + word for a pass / warn / fail / not-checked status, so colour is never the only signal. */
export function StatusBadge({ status }) {
  const meta = {
    pass: { icon: 'check', text: 'Pass' },
    warn: { icon: 'warn', text: 'Warning' },
    fail: { icon: 'cross', text: 'Fail' },
    na: { icon: 'info', text: 'Not checked' },
  }[status];
  return (
    <span className={`status-badge status-badge--${status}`}>
      <Icon name={meta.icon} size={16} />
      {meta.text}
    </span>
  );
}
