// Shared TypeScript types — mirrors the FastAPI Pydantic models

export interface Project {
  id: string;
  name: string;
  description?: string;
  commodity?: string;
  study_type: "PEA" | "PFS" | "FS" | "scoping" | "other";
  ticker?: string | null;
  created_at: string;
  status: "empty" | "ingested" | "analyzed" | "error";
  file_count: number;
  run_count: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  commodity?: string;
  study_type: "PEA" | "PFS" | "FS" | "scoping" | "other";
}

export interface FileRecord {
  filename: string;
  path: string;
  size_bytes: number;
  mime_type?: string;
  ingested: boolean;
  ingested_at?: string;
  uploaded_at?: string;
  page_count?: number;
  error?: string;
}

export interface IngestResponse {
  project_id: string;
  queued: string[];
  skipped: string[];
  errors: string[];
}

export interface RunStatus {
  run_id: string;
  project_id: string;
  status: "pending" | "running" | "complete" | "failed";
  started_at?: string;
  completed_at?: string;
  step?: string;
  error?: string;
  output_files: string[];
}

export interface ReportContent {
  run_id: string;
  project_id: string;
  sections: Record<string, unknown>;
}

export interface AppSettings {
  openai_api_key?: string;
  anthropic_api_key?: string;
}

export type RoyaltyType = "NSR" | "GR" | "NPI" | "Stream" | "Sliding NSR" | "Production" | "Other";

export interface Royalty {
  royalty_id: string;
  royalty_type: RoyaltyType;
  holder: string;
  rate_pct?: number | null;
  metals_covered?: string | null;
  area_covered?: string | null;
  stream_pct?: number | null;
  stream_purchase_price?: number | null;
  stream_purchase_unit?: string | null;
  sliding_scale_notes?: string | null;
  production_rate?: number | null;
  production_unit?: string | null;
  buyback_option: boolean;
  buyback_price_musd?: number | null;
  recorded_instrument?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoyaltyWarning {
  level: "critical" | "caution" | "info";
  message: string;
}

export interface RoyaltySummary {
  project_id: string;
  total_agreements: number;
  nsr_equivalent_pct?: number | null;
  has_stream: boolean;
  has_npi: boolean;
  holders: string[];
  metals_affected: string[];
  buyback_options: number;
  warnings: RoyaltyWarning[];
}

export interface ResourceRow {
  row_id: string;
  classification: "Measured" | "Indicated" | "Inferred";
  domain?: string | null;
  tonnage_mt?: number | null;
  grade_value?: number | null;
  grade_unit?: string | null;
  contained_metal?: number | null;
  metal_unit?: string | null;
  cut_off_grade?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResourceWarning {
  level: "critical" | "caution" | "info";
  message: string;
}

export interface ResourceSummary {
  project_id: string;
  total_tonnage_mt?: number | null;
  measured_mt?: number | null;
  indicated_mt?: number | null;
  inferred_mt?: number | null;
  inferred_pct?: number | null;
  metal_unit?: string | null;
  total_contained?: number | null;
  measured_indicated_contained?: number | null;
  inferred_contained?: number | null;
  warnings: ResourceWarning[];
}

export interface Comparable {
  comp_id: string;
  project_name: string;
  acquirer?: string | null;
  seller?: string | null;
  commodity?: string | null;
  transaction_date?: string | null;
  transaction_value_musd?: number | null;
  resource_moz_or_mlb?: number | null;
  price_per_unit_usd?: number | null;
  study_stage?: string | null;
  jurisdiction?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Note {
  note_id: string;
  content: string;
  tag?: string | null;
  created_at: string;
  updated_at: string;
}

export type NewsCategory =
  | "resource_update" | "financing" | "permitting" | "acquisition"
  | "production" | "management" | "esg" | "market" | "other";

export interface NewsItem {
  news_id: string;
  headline: string;
  date: string;
  source: string;
  url?: string | null;
  summary: string;
  category: NewsCategory;
  sentiment: "positive" | "negative" | "neutral";
  relevance: "high" | "medium" | "low";
  tags: string[];
}

export interface NewsFeed {
  fetched_at: string;
  project_name: string;
  commodity: string;
  jurisdiction?: string | null;
  items: NewsItem[];
  error?: string | null;
}

export interface PortfolioNewsItem extends NewsItem {
  project_id: string;
  project_name: string;
}

export interface NpvRefreshResult {
  new_npv_musd: number | null;
  last_npv_musd: number | null;
  npv_delta_pct: number | null;
  new_irr_pct: number | null;
  last_irr_pct: number | null;
  commodity: string | null;
  current_price: number | null;
  last_price: number | null;
  price_change_pct: number | null;
  refreshed_at: string;
  error?: string | null;
}
