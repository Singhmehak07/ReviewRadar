import type { BatchResponse, ReviewResult, RiskBand } from "@/lib/types";

type ResultPanelProps = {
  single: ReviewResult | null;
  batch: BatchResponse | null;
};

function bandClass(band: RiskBand) {
  const safeBand = (band || "Low").toString().toLowerCase();
  return `band-${safeBand}`;
}

function ScoreDial({ score = 0, band = "Low", label = "Average computer-generated writing risk" }: { score?: number; band?: RiskBand; label?: string }) {
  const safeScore = typeof score === "number" ? score : 0;
  const safeBand = band || "Low";
  const safeLabel = label || "Average computer-generated writing risk";
  const radius = 47;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(Math.max(safeScore, 0), 100) / 100) * circumference;
  return (
    <div className={`score-dial ${bandClass(safeBand)}`}>
      <svg viewBox="0 0 120 120" role="img" aria-label={`${safeLabel}: ${safeScore.toFixed(1)} percent, ${safeBand} risk`}>
        <circle className="dial-track" cx="60" cy="60" r={radius} />
        <circle
          className="dial-value"
          cx="60"
          cy="60"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="dial-number"><strong>{safeScore.toFixed(1)}</strong><span>%</span></div>
    </div>
  );
}

function AdditionalSignalsList({ reasons = [] }: { reasons?: string[] }) {
  const safeReasons = Array.isArray(reasons) ? reasons : [];
  if (safeReasons.length === 0) return null;
  return (
    <div className="evidence-block">
      <h4>Additional signals</h4>
      <ul>
        {safeReasons.map((reason, index) => (
          <li key={`${reason}-${index}`}><span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span><p>{reason}</p></li>
        ))}
      </ul>
    </div>
  );
}

function SingleResult({ result }: { result: ReviewResult }) {
  const score = result?.risk_score ?? 0;
  const band = result?.risk_band ?? "Low";
  const label = result?.risk_label ?? "Average computer-generated writing risk";
  const interpretation = result?.interpretation || { headline: "Analysis complete", description: "No interpretation available." };
  const reasons = result?.reasons || [];
  const cleanedText = result?.cleaned_text ?? "";
  const cleaning = result?.cleaning || { original_character_count: 0, cleaned_character_count: 0, removed_noise_lines: [] };
  const removedNoiseLines = cleaning.removed_noise_lines || [];
  const disclaimer = result?.disclaimer ?? "Highlights suspicious review patterns; does not prove fraud.";

  return (
    <section className="result-panel" aria-labelledby="single-result-title">
      <div className="result-summary">
        <ScoreDial score={score} band={band} label={label} />
        <div>
          <p className={`band-label ${bandClass(band)}`}>{band} risk</p>
          <h3 id="single-result-title">{interpretation.headline || "Analysis complete"}</h3>
          <p>{interpretation.description || "No interpretation available."}</p>
        </div>
      </div>

      <p style={{ marginTop: "16px", fontSize: "14px", color: "var(--ink-soft)" }}>
        This score is based on how the review’s overall writing pattern compares with the model’s training examples.
      </p>

      <AdditionalSignalsList reasons={reasons} />

      <details className="cleaned-review">
        <summary>View cleaned review</summary>
        <blockquote>{cleanedText}</blockquote>
        <p>{removedNoiseLines.length} copied interface line{removedNoiseLines.length === 1 ? "" : "s"} removed.</p>
      </details>

      <p className="result-disclaimer">{disclaimer}</p>
    </section>
  );
}

function Distribution({ batch }: { batch: BatchResponse }) {
  const summary = batch?.summary;
  const total = Math.max(summary?.reviews_analyzed ?? 0, 1);
  const distribution = summary?.distribution || { Low: 0, Moderate: 0, High: 0 };
  const bands: RiskBand[] = ["Low", "Moderate", "High"];
  return (
    <div className="distribution" aria-label="Risk-band distribution">
      {bands.map((band) => {
        const count = distribution[band] || 0;
        return (
          <div className="distribution-row" key={band}>
            <div><span>{band}</span><strong>{count}</strong></div>
            <div className="bar-track" aria-hidden="true">
              <span className={bandClass(band)} style={{ width: `${(count / total) * 100}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BatchResult({ batch }: { batch: BatchResponse }) {
  const summary = batch?.summary || {
    overall_risk_score: 0,
    overall_band: "Low",
    overall_risk_label: "Average computer-generated writing risk",
    overall_interpretation: { headline: "Batch Analysis Complete", description: "No description available." },
    reviews_analyzed: 0,
    reviews_submitted: 0,
    pct_computer_generated: 0,
    count_flagged: 0,
    duplicate_reviews: 0,
    duplicate_groups: 0,
    sample_notice: "",
  };
  const results = batch?.results || [];
  const headline = batch?.headline ?? "Batch analysis completed.";
  const disclaimer = batch?.disclaimer ?? "Highlights suspicious review patterns; does not prove fraud.";

  const overallScore = summary.overall_risk_score ?? 0;
  const overallBand = summary.overall_band ?? "Low";
  const overallLabel = summary.overall_risk_label ?? "Average computer-generated writing risk";
  const overallInterp = summary.overall_interpretation || { headline: "Batch Analysis Complete", description: "No description available." };

  const reviewsAnalyzed = summary.reviews_analyzed ?? 0;
  const reviewsSubmitted = summary.reviews_submitted ?? 0;
  const pctComputerGenerated = summary.pct_computer_generated ?? 0;
  const countFlagged = summary.count_flagged ?? 0;
  const duplicateReviews = summary.duplicate_reviews ?? 0;
  const duplicateGroups = summary.duplicate_groups ?? 0;
  const sampleNotice = summary.sample_notice ?? "";

  return (
    <section className="result-panel batch-result" aria-labelledby="batch-result-title">
      <div className="result-summary">
        <ScoreDial score={overallScore} band={overallBand} label={overallLabel} />
        <div>
          <p className={`band-label ${bandClass(overallBand)}`}>{overallBand} average risk</p>
          <h3 id="batch-result-title">{overallInterp.headline || "Batch Analysis Complete"}</h3>
          <p>{headline}</p>
        </div>
      </div>

      <p style={{ marginTop: "16px", fontSize: "14px", color: "var(--ink-soft)" }}>
        This score is based on how the review’s overall writing pattern compares with the model’s training examples.
      </p>

      <div className="batch-metrics">
        <div><span>Analyzed</span><strong>{reviewsAnalyzed}</strong><small>of {reviewsSubmitted}</small></div>
        <div><span>Flagged high</span><strong>{pctComputerGenerated.toFixed(1)}%</strong><small>{countFlagged} reviews</small></div>
        <div><span>Duplicates</span><strong>{duplicateReviews}</strong><small>{duplicateGroups} groups</small></div>
      </div>

      <Distribution batch={batch} />

      <details className="review-breakdown">
        <summary>Review-by-review breakdown <span>{results.length}</span></summary>
        <div className="review-list">
          {results.map((result, index) => {
            const resScore = result?.risk_score ?? 0;
            const resBand = result?.risk_band ?? "Low";
            const resCleanedText = result?.cleaned_text ?? "";
            const resReasons = result?.reasons || [];
            return (
              <article key={`${result?.review_index ?? index}-${resScore}`}>
                <div className="review-list-head">
                  <span>Review {(result?.review_index ?? index) + 1}</span>
                  <strong className={bandClass(resBand)}>{resScore.toFixed(1)}% · {resBand}</strong>
                </div>
                <p>{resCleanedText}</p>
                <ul>{resReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
              </article>
            );
          })}
        </div>
      </details>

      <p className="result-disclaimer">{sampleNotice} {disclaimer}</p>
    </section>
  );
}

export function ResultPanel({ single, batch }: ResultPanelProps) {
  if (single) return <SingleResult result={single} />;
  if (batch) return <BatchResult batch={batch} />;
  return null;
}

