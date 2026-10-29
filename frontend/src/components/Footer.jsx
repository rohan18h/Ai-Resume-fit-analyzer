export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__inner">
        <p className="site-footer__title">AI-Powered Resume Fit Analyzer</p>
        <p>Mini Project · TY Computer Engineering</p>
        <p>Team: [Names] · Guide: [Guide name]</p>
        <p className="site-footer__note">
          Responsible use: the fit score is an estimate to help applicants improve. It must not be used to make
          hiring decisions about people.
        </p>
        <p className="site-footer__note">
          Privacy: your resume and job description are processed in memory and never stored.
        </p>
      </div>
    </footer>
  );
}
