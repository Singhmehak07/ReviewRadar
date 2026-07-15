import { ReviewAnalyzer } from "@/components/ReviewAnalyzer";
import { RadarMark } from "@/components/RadarMark";

export default function Home() {
  return (
    <>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="ReviewRadar home">
          <RadarMark size={30} />
          <span>ReviewRadar</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#analyzer">Analyzer</a>
          <a href="#method">Method</a>
          <a href="https://github.com/Singhmehak07/ReviewRadar" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="hero shell" aria-labelledby="page-title">
          <div className="hero-copy">
            <p className="eyebrow">Explainable review screening</p>
            <h1 id="page-title">Analyze reviews. Spot suspicious patterns.</h1>
            <p className="hero-lede">
              ReviewRadar checks individual reviews and batches for writing patterns associated with computer-generated text.
            </p>
            <div className="hero-note">
              <span className="hero-note-mark" aria-hidden="true">01</span>
              <p>No scraping. Paste reviews from any marketplace or upload a CSV.</p>
            </div>
          </div>

          <div id="analyzer" className="analyzer-wrap">
            <ReviewAnalyzer />
          </div>
        </section>

        <section id="method" className="method shell" aria-labelledby="method-title">
          <div className="section-heading">
            <p className="eyebrow">How to read the result</p>
            <h2 id="method-title">Evidence before certainty.</h2>
          </div>
          <ol className="method-list">
            <li>
              <span>01</span>
              <h3>Model score</h3>
              <p>TF-IDF and Logistic Regression estimate similarity to the computer-generated training class.</p>
            </li>
            <li>
              <span>02</span>
              <h3>Phrase evidence</h3>
              <p>Active words and phrases are ranked by their positive contribution toward that class.</p>
            </li>
            <li>
              <span>03</span>
              <h3>Supporting context</h3>
              <p>Optional rating conflicts and exact duplicates are shown separately; they never rewrite the model score.</p>
            </li>
          </ol>
        </section>
      </main>

      <footer className="site-footer shell">
        <p>Built by Mehakpreet Singh · Machine learning project</p>
        <p>Signals, not verdicts.</p>
      </footer>
    </>
  );
}
