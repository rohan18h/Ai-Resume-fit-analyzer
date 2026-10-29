import { NavLink, Link } from 'react-router-dom';

const NAV = [
  { to: '/', label: 'Analyzer', end: true },
  { to: '/how-it-works', label: 'How it works' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/about', label: 'About' },
];

export default function Header() {
  return (
    <header className="site-header">
      <div className="container site-header__inner">
        <Link to="/" className="site-header__logo">Resume Fit Analyzer</Link>
        <nav aria-label="Main">
          <ul className="site-nav">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className="site-nav__link">
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
