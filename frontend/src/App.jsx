import { Routes, Route } from 'react-router-dom';
import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import Analyzer from './pages/Analyzer.jsx';
import HowItWorks from './pages/HowItWorks.jsx';
import Evaluation from './pages/Evaluation.jsx';
import About from './pages/About.jsx';
import NotFound from './pages/NotFound.jsx';

export default function App() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">Skip to content</a>
      <Header />
      <main id="main" className="container">
        <Routes>
          <Route path="/" element={<Analyzer />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/evaluation" element={<Evaluation />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
