// API client — thin wrapper around the FastAPI backend

import type {
  AppSettings,
  Comparable,
  FileRecord,
  IngestResponse,
  NewsFeed,
  NpvRefreshResult,
  PortfolioNewsItem,
  Note,
  Project,
  ProjectCreate,
  ReportContent,
  ResourceRow,
  ResourceSummary,
  Royalty,
  RoyaltySummary,
  RunStatus,
} from "../types";

// In production (Tauri bundle) there's no Vite proxy, so we hit the API
// directly on localhost.  In development the Vite proxy forwards /api → 8000.
const BASE = import.meta.env.PROD
  ? "http://127.0.0.1:8000"
  : "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// ── Projects ────────────────────────────────────────────────────────────────

export async function listProjects(): Promise<Project[]> {
  const data = await request<{ projects: Project[] }>("/projects");
  return data.projects;
}

export async function createProject(body: ProjectCreate): Promise<Project> {
  return request("/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getProject(id: string): Promise<Project> {
  return request(`/projects/${id}`);
}

export async function renameProject(id: string, name: string): Promise<Project> {
  return request(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function patchProject(id: string, updates: { name?: string; ticker?: string | null }): Promise<Project> {
  return request(`/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function archiveProject(id: string): Promise<void> {
  return request(`/projects/${id}/archive`, { method: "POST" });
}

export async function deleteProject(id: string): Promise<void> {
  return request(`/projects/${id}`, { method: "DELETE" });
}

// ── Files ───────────────────────────────────────────────────────────────────

export async function listFiles(projectId: string): Promise<FileRecord[]> {
  const data = await request<{ files: FileRecord[] }>(`/projects/${projectId}/files`);
  return data.files;
}

export async function uploadFiles(
  projectId: string,
  files: File[]
): Promise<IngestResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE}/projects/${projectId}/files`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

export async function deleteFile(projectId: string, filename: string): Promise<void> {
  return request(`/projects/${projectId}/files/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
}

export async function ingestUrl(
  projectId: string,
  url: string,
): Promise<{ filename: string; url: string; size_bytes: number; status: string }> {
  return request(`/projects/${projectId}/ingest/url`, {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

// ── Analysis ────────────────────────────────────────────────────────────────

export async function startAnalysis(projectId: string): Promise<RunStatus> {
  return request(`/projects/${projectId}/analyze`, {
    method: "POST",
    body: JSON.stringify({ force: false }),
  });
}

export async function refreshNpv(projectId: string): Promise<NpvRefreshResult> {
  return request(`/projects/${projectId}/npv-refresh`, { method: "POST" });
}

export async function listRuns(projectId: string): Promise<RunStatus[]> {
  const data = await request<{ runs: RunStatus[] }>(`/projects/${projectId}/runs`);
  return data.runs;
}

export async function getRun(projectId: string, runId: string): Promise<RunStatus> {
  return request(`/projects/${projectId}/runs/${runId}`);
}

export async function deleteRun(projectId: string, runId: string): Promise<void> {
  return request(`/projects/${projectId}/runs/${runId}`, { method: "DELETE" });
}

// ── Reports ─────────────────────────────────────────────────────────────────

export async function getReport(
  projectId: string,
  runId: string
): Promise<ReportContent> {
  return request(`/projects/${projectId}/reports/${runId}`);
}

// ── Notes ────────────────────────────────────────────────────────────────────

export async function listNotes(projectId: string): Promise<Note[]> {
  const data = await request<{ notes: Note[] }>(`/projects/${projectId}/notes`);
  return data.notes;
}

export async function createNote(
  projectId: string,
  content: string,
  tag?: string,
): Promise<Note> {
  return request(`/projects/${projectId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content, tag: tag ?? null }),
  });
}

export async function updateNote(
  projectId: string,
  noteId: string,
  content: string,
  tag?: string | null,
): Promise<Note> {
  return request(`/projects/${projectId}/notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify({ content, tag }),
  });
}

export async function deleteNote(projectId: string, noteId: string): Promise<void> {
  return request(`/projects/${projectId}/notes/${noteId}`, { method: "DELETE" });
}

// ── Resources ────────────────────────────────────────────────────────────────

export async function listResources(projectId: string): Promise<ResourceRow[]> {
  return request<ResourceRow[]>(`/projects/${projectId}/resources`);
}

export async function createResource(
  projectId: string,
  body: Omit<ResourceRow, "row_id" | "created_at" | "updated_at">,
): Promise<ResourceRow> {
  return request(`/projects/${projectId}/resources`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteResource(projectId: string, rowId: string): Promise<void> {
  return request(`/projects/${projectId}/resources/${rowId}`, { method: "DELETE" });
}

export async function getResourceSummary(projectId: string): Promise<ResourceSummary> {
  return request<ResourceSummary>(`/projects/${projectId}/resources/summary`);
}

// ── Royalties ────────────────────────────────────────────────────────────────

export async function listRoyalties(projectId: string): Promise<Royalty[]> {
  return request<Royalty[]>(`/projects/${projectId}/royalties`);
}

export async function createRoyalty(
  projectId: string,
  body: Omit<Royalty, "royalty_id" | "created_at" | "updated_at">,
): Promise<Royalty> {
  return request(`/projects/${projectId}/royalties`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteRoyalty(projectId: string, royaltyId: string): Promise<void> {
  return request(`/projects/${projectId}/royalties/${royaltyId}`, { method: "DELETE" });
}

export async function getRoyaltySummary(projectId: string): Promise<RoyaltySummary> {
  return request<RoyaltySummary>(`/projects/${projectId}/royalties/summary`);
}

// ── Comparables ──────────────────────────────────────────────────────────────

export async function listComparables(projectId: string): Promise<Comparable[]> {
  const data = await request<{ comparables: Comparable[] }>(`/projects/${projectId}/comparables`);
  return data.comparables;
}

export async function createComparable(
  projectId: string,
  body: Omit<Comparable, "comp_id" | "created_at" | "updated_at">,
): Promise<Comparable> {
  return request(`/projects/${projectId}/comparables`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteComparable(projectId: string, compId: string): Promise<void> {
  return request(`/projects/${projectId}/comparables/${compId}`, { method: "DELETE" });
}

// ── Drill Holes ───────────────────────────────────────────────────────────────

export interface DrillCollar {
  hole_id: string;
  x: number | null;
  y: number | null;
  z: number | null;
  depth: number | null;
  azimuth: number | null;
  dip: number | null;
}

export interface DrillAssay {
  hole_id: string;
  from_m: number | null;
  to_m: number | null;
  length: number | null;
  [analyte: string]: number | string | null;
}

export interface TracePoint { depth: number; x: number; y: number; z: number; }

export interface DrillholeDataset {
  project_id: string;
  collars: DrillCollar[];
  surveys: object[];
  assays: DrillAssay[];
  traces: Record<string, TracePoint[]>;
  analytes: string[];
  hole_count: number;
  updated_at: string | null;
}

export interface DrillholeSummary {
  project_id: string;
  hole_count: number;
  has_surveys: boolean;
  has_assays: boolean;
  analytes: string[];
  assay_stats: Record<string, { count: number; min: number; max: number; mean: number; p90: number }>;
  total_metres: number;
  updated_at: string | null;
}

export interface DrillUploadResult {
  project_id: string;
  table_type: string;
  filename: string;
  hole_count: number;
  row_count: number;
  analytes: string[];
  error?: string | null;
}

export async function getDrillholes(projectId: string): Promise<DrillholeDataset> {
  return request<DrillholeDataset>(`/projects/${projectId}/drillholes`);
}

export async function getDrillholeSummary(projectId: string): Promise<DrillholeSummary> {
  return request<DrillholeSummary>(`/projects/${projectId}/drillholes/summary`);
}

export async function uploadDrillholeFile(projectId: string, file: File): Promise<DrillUploadResult> {
  const form = new FormData();
  form.append("file", file);
  return request<DrillUploadResult>(`/projects/${projectId}/drillholes/upload`, { method: "POST", body: form });
}

export async function deleteDrillholes(projectId: string): Promise<void> {
  return request(`/projects/${projectId}/drillholes`, { method: "DELETE" });
}

// ── EDGAR / SEDAR Filing Import ───────────────────────────────────────────────

export interface EdgarCompany {
  cik: string;
  name: string;
  ticker: string;
  exchange: string;
}

export interface EdgarFiling {
  accession_number: string;
  form_type: string;
  filing_date: string;
  report_date: string;
  primary_document: string;
  primary_doc_description: string;
  filing_url: string;
  index_url: string;
  cik: string;
}

export interface EdgarDocument {
  filename: string;
  description: string;
  document_type: string;
  size_bytes: number;
  url: string;
}

export interface FilingImportResponse {
  project_id: string;
  filename: string;
  url: string;
  size_bytes: number;
  source: string;
  status: string;
  error?: string | null;
}

export async function edgarSearchCompanies(q: string): Promise<{ results: EdgarCompany[]; total: number }> {
  return request(`/edgar/search?q=${encodeURIComponent(q)}&limit=12`);
}

export async function edgarListFilings(cik: string, forms?: string): Promise<{ company: string; ticker: string; filings: EdgarFiling[]; total: number }> {
  const formsParam = forms ? `&forms=${encodeURIComponent(forms)}` : "";
  return request(`/edgar/filings?cik=${encodeURIComponent(cik)}${formsParam}&limit=30`);
}

export async function edgarListDocuments(cik: string, accession: string): Promise<{ documents: EdgarDocument[]; total: number }> {
  return request(`/edgar/filings/${encodeURIComponent(cik)}/${encodeURIComponent(accession)}/documents`);
}

export async function importFilingDocument(projectId: string, url: string, filename?: string, source?: string): Promise<FilingImportResponse> {
  return request(`/projects/${projectId}/files/import-filing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, filename: filename ?? null, source: source ?? "edgar" }),
  });
}

export async function getSedarSearchLink(company: string): Promise<{ search_url: string; note: string }> {
  return request(`/sedar/search-link?company=${encodeURIComponent(company)}`);
}

// ── News ─────────────────────────────────────────────────────────────────────

export async function getProjectNews(projectId: string): Promise<NewsFeed> {
  return request<NewsFeed>(`/projects/${projectId}/news`);
}

export async function refreshProjectNews(projectId: string): Promise<NewsFeed> {
  return request<NewsFeed>(`/projects/${projectId}/news/refresh`, { method: "POST" });
}

export async function getPortfolioNews(limit = 50): Promise<{ items: PortfolioNewsItem[]; total: number }> {
  return request(`/portfolio/news?limit=${limit}`);
}

// ── Jurisdiction Risk ────────────────────────────────────────────────────────

export interface JurisdictionRisk {
  id: string;
  name: string;
  country: string;
  region: string;
  risk_tier: 1 | 2 | 3 | 4;
  risk_level: "low" | "moderate" | "high" | "very_high";
  political_stability: "very_high" | "high" | "moderate" | "low" | "very_low";
  fraser_rank_approx?: number | null;
  permitting_timeline_months?: number | null;
  corporate_tax_rate_pct?: number | null;
  royalty_type?: string | null;
  royalty_rate?: string | null;
  key_strengths: string[];
  key_risks: string[];
  recent_policy_notes?: string | null;
  summary?: string | null;
  not_found?: boolean;
  reason?: string;
}

export async function getProjectJurisdictionRisk(projectId: string): Promise<JurisdictionRisk> {
  return request<JurisdictionRisk>(`/projects/${projectId}/jurisdiction-risk`);
}

export async function lookupJurisdiction(name: string): Promise<JurisdictionRisk> {
  return request<JurisdictionRisk>(`/tools/jurisdiction/${encodeURIComponent(name)}`);
}

// ── Sanity Check ─────────────────────────────────────────────────────────────

export interface SanityFlag {
  level: "critical" | "warning" | "ok" | "info";
  category: string;
  field: string;
  value: string;
  message: string;
  expected_range?: string | null;
}

export interface SanityResult {
  project_id: string;
  has_report: boolean;
  flags: SanityFlag[];
  critical_count: number;
  warning_count: number;
  ok_count: number;
  overall: "critical" | "warning" | "ok" | "no_data";
}

export async function runSanityCheck(projectId: string): Promise<SanityResult> {
  return request<SanityResult>(`/projects/${projectId}/sanity`);
}

// ── Portfolio ────────────────────────────────────────────────────────────────

export interface ProjectMetrics {
  project_id: string;
  name: string;
  commodity?: string | null;
  study_type?: string | null;
  status?: string | null;
  has_report: boolean;
  total_resource_mt?: number | null;
  mi_resource_mt?: number | null;
  inferred_pct?: number | null;
  primary_grade?: number | null;
  grade_unit?: string | null;
  total_contained?: number | null;
  metal_unit?: string | null;
  npv_musd?: number | null;
  irr_pct?: number | null;
  payback_years?: number | null;
  initial_capex_musd?: number | null;
  aisc_per_oz?: number | null;
  opex_per_tonne?: number | null;
  jurisdiction?: string | null;
  operator?: string | null;
  mine_life_years?: number | null;
  nsr_burden_pct?: number | null;
  has_stream: boolean;
  file_count: number;
  run_count: number;
  notes_count: number;
  comparables_count: number;
}

export async function getPortfolioProjects(): Promise<Array<{ id: string; name: string; commodity?: string; study_type?: string; status?: string }>> {
  const data = await request<{ projects: Array<{ id: string; name: string; commodity?: string; study_type?: string; status?: string }> }>("/portfolio/projects");
  return data.projects;
}

export async function comparePortfolio(ids: string[]): Promise<ProjectMetrics[]> {
  const data = await request<{ projects: ProjectMetrics[] }>(`/portfolio/compare?ids=${ids.join(",")}`);
  return data.projects;
}

// ── Settings ─────────────────────────────────────────────────────────────────

export async function getSettings(): Promise<AppSettings> {
  return request("/settings");
}

export async function saveSettings(body: AppSettings): Promise<AppSettings> {
  return request("/settings", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── License ───────────────────────────────────────────────────────────────────

export async function activateLicense(licenseKey: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${BASE}/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ license_key: licenseKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Activation failed");
  }
  return res.json();
}

export function exportUrl(
  projectId: string,
  runId: string,
  format: "json" | "md" | "txt" | "pptx" = "md"
): string {
  return `${BASE}/projects/${projectId}/reports/${runId}/export?format=${format}`;
}
