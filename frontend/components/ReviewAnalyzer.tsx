"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { analyzeBatch, analyzeCsv, analyzeSingle, checkHealth } from "@/lib/api";
import type { AnalyzerMode, BatchResponse, ReviewResult } from "@/lib/types";
import { ResultPanel } from "./ResultPanel";

const MODES: Array<{ id: AnalyzerMode; label: string; hint: string }> = [
  { id: "single", label: "One review", hint: "Score one review with an optional rating." },
  { id: "batch", label: "Review batch", hint: "Separate reviews with a blank line." },
  { id: "csv", label: "CSV upload", hint: "Use a review_text column; rating is optional." },
];

const SINGLE_SAMPLE =
  "The keyboard has a firm feel, the keys are quiet, and setup took less than five minutes.";

const BATCH_SAMPLE = `The fabric stayed soft after two washes and the stitching still looks clean.

Amazing product, best quality, highly recommended to everyone!

The lid is difficult to close when the container is completely full.`;

export function ReviewAnalyzer() {
  const [mode, setMode] = useState<AnalyzerMode>("single");
  const [singleText, setSingleText] = useState("");
  const [batchText, setBatchText] = useState("");
  const [rating, setRating] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [singleResult, setSingleResult] = useState<ReviewResult | null>(null);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "ready" | "error">("checking");

  useEffect(() => {
    let active = true;
    checkHealth().then((ok) => {
      if (active) {
        setApiStatus(ok ? "ready" : "error");
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const batchReviews = useMemo(
    () => batchText.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean),
    [batchText],
  );

  function selectMode(nextMode: AnalyzerMode) {
    setMode(nextMode);
    setError("");
    setSingleResult(null);
    setBatchResult(null);
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % MODES.length;
    if (event.key === "ArrowLeft") next = (index - 1 + MODES.length) % MODES.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = MODES.length - 1;
    selectMode(MODES[next].id);
    document.getElementById(`tab-${MODES[next].id}`)?.focus();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSingleResult(null);
    setBatchResult(null);

    if (mode === "single" && !singleText.trim()) {
      setError("Paste a review before starting the analysis.");
      return;
    }
    if (mode === "batch" && batchReviews.length === 0) {
      setError("Add at least one review. Separate multiple reviews with a blank line.");
      return;
    }
    if (mode === "batch" && batchReviews.length > 100) {
      setError("A batch can contain at most 100 reviews.");
      return;
    }
    if (mode === "csv" && !file) {
      setError("Choose a CSV file before starting the analysis.");
      return;
    }

    setLoading(true);
    try {
      if (mode === "single") {
        const result = await analyzeSingle(singleText.trim(), rating ? Number(rating) : undefined);
        setSingleResult(result);
      } else if (mode === "batch") {
        setBatchResult(await analyzeBatch(batchReviews));
      } else if (file) {
        setBatchResult(await analyzeCsv(file));
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The analysis could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  function chooseFile(nextFile: File | null) {
    setError("");
    if (!nextFile) {
      setFile(null);
      return;
    }
    if (!nextFile.name.toLowerCase().endsWith(".csv")) {
      setError("Choose a file with a .csv extension.");
      setFile(null);
      return;
    }
    if (nextFile.size > 5 * 1024 * 1024) {
      setError("The CSV must be 5 MB or smaller.");
      setFile(null);
      return;
    }
    setFile(nextFile);
  }

  const activeMode = MODES.find((item) => item.id === mode)!;

  const statusColor = apiStatus === "checking" ? "var(--muted)" : apiStatus === "ready" ? "var(--green)" : "var(--red)";
  const statusShadow = apiStatus === "checking" ? "var(--surface-soft)" : apiStatus === "ready" ? "var(--green-soft)" : "var(--red-soft)";
  const statusText = apiStatus === "checking" ? "Checking API status..." : apiStatus === "ready" ? "API ready" : "API connection error";

  return (
    <section className="analyzer" aria-labelledby="analyzer-title" aria-busy={loading}>
      <div className="analyzer-head">
        <div>
          <p className="analyzer-kicker">Analyzer</p>
          <h2 id="analyzer-title">Check the writing pattern</h2>
        </div>
        <span className="api-state">
          <span
            aria-hidden="true"
            style={{
              background: statusColor,
              boxShadow: `0 0 0 4px ${statusShadow}`,
            }}
          />
          {statusText}
        </span>
      </div>

      <div className="mode-tabs" role="tablist" aria-label="Choose analysis input">
        {MODES.map((item, index) => (
          <button
            id={`tab-${item.id}`}
            key={item.id}
            type="button"
            role="tab"
            aria-selected={mode === item.id}
            aria-controls={`panel-${item.id}`}
            tabIndex={mode === item.id ? 0 : -1}
            onClick={() => selectMode(item.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div
          id={`panel-${mode}`}
          role="tabpanel"
          aria-labelledby={`tab-${mode}`}
          className="input-panel"
        >
          <div className="field-heading">
            <label htmlFor={mode === "csv" ? "csv-file" : `${mode}-text`}>{activeMode.label}</label>
            <span>{activeMode.hint}</span>
          </div>

          {mode === "single" && (
            <>
              <textarea
                id="single-text"
                value={singleText}
                onChange={(event) => setSingleText(event.target.value)}
                placeholder="Paste the complete review here…"
                rows={8}
                maxLength={10000}
                aria-describedby="single-help"
              />
              <div className="field-meta" id="single-help">
                <button type="button" className="text-action" onClick={() => setSingleText(SINGLE_SAMPLE)}>
                  Use a sample
                </button>
                <span>{singleText.length.toLocaleString()} / 10,000</span>
              </div>
              <label className="rating-field" htmlFor="rating">
                <span>Star rating <small>optional</small></span>
                <select id="rating" value={rating} onChange={(event) => setRating(event.target.value)}>
                  <option value="">Not provided</option>
                  {[1, 2, 3, 4, 5].map((value) => (
                    <option key={value} value={value}>{value} star{value === 1 ? "" : "s"}</option>
                  ))}
                </select>
              </label>
            </>
          )}

          {mode === "batch" && (
            <>
              <textarea
                id="batch-text"
                value={batchText}
                onChange={(event) => setBatchText(event.target.value)}
                placeholder={"First review…\n\nSecond review…\n\nThird review…"}
                rows={10}
                aria-describedby="batch-help"
              />
              <div className="field-meta" id="batch-help">
                <button type="button" className="text-action" onClick={() => setBatchText(BATCH_SAMPLE)}>
                  Use a sample batch
                </button>
                <span>{batchReviews.length} / 100 reviews</span>
              </div>
            </>
          )}

          {mode === "csv" && (
            <div className={`file-drop ${file ? "has-file" : ""}`}>
              <input
                id="csv-file"
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => chooseFile(event.target.files?.[0] || null)}
              />
              <label htmlFor="csv-file">
                <span className="file-icon" aria-hidden="true">↥</span>
                <strong>{file ? file.name : "Choose a CSV file"}</strong>
                <span>{file ? `${(file.size / 1024).toFixed(1)} KB selected` : "review_text required · rating optional · 5 MB maximum"}</span>
              </label>
              {file && (
                <button type="button" className="remove-file" onClick={() => chooseFile(null)}>
                  Remove file
                </button>
              )}
            </div>
          )}
        </div>

        {error && <div className="form-alert" role="alert">{error}</div>}

        <div className="submit-row">
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? <><span className="spinner" aria-hidden="true" /> Analyzing</> : "Analyze reviews"}
          </button>
          <p>Only submitted text is analyzed.</p>
        </div>
      </form>

      <div className="status-region" aria-live="polite" aria-atomic="true">
        {loading && <p className="loading-note">The free API may need a moment to wake up.</p>}
      </div>

      {(singleResult || batchResult) && (
        <ResultPanel single={singleResult} batch={batchResult} />
      )}
    </section>
  );
}
