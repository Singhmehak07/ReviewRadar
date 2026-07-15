export type RiskBand = "Low" | "Moderate" | "High";

export type Interpretation = {
  headline: string;
  description: string;
};

export type CleaningDetails = {
  original_character_count: number;
  cleaned_character_count: number;
  removed_noise_lines: string[];
  extracted_rating: number | null;
};

export type ReviewResult = {
  cleaned_text: string;
  risk_score: number;
  risk_band: RiskBand;
  risk_label: string;
  interpretation: Interpretation;
  reasons: string[];
  cleaning: CleaningDetails;
  disclaimer: string;
  consistency_flag?: string;
  review_index?: number;
  duplicate?: boolean;
  duplicate_group?: string | null;
};

export type BatchSummary = {
  reviews_submitted: number;
  reviews_analyzed: number;
  reviews_skipped: number;
  overall_risk_score: number;
  overall_band: RiskBand;
  overall_risk_label: string;
  overall_interpretation: Interpretation;
  flagged_percentage_label: string;
  count_flagged: number;
  pct_computer_generated: number;
  distribution: Record<RiskBand, number>;
  duplicate_reviews: number;
  duplicate_groups: number;
  sample_notice: string;
};

export type BatchResponse = {
  headline: string;
  results: ReviewResult[];
  summary: BatchSummary;
  disclaimer: string;
  message: string;
};

export type AnalyzerMode = "single" | "batch" | "csv";
