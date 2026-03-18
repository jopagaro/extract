// Shared TypeScript types — mirrors the FastAPI Pydantic models

export interface Project {
  id: string;
  name: string;
  description?: string;
  commodity?: string;
  study_type: "PEA" | "PFS" | "FS" | "scoping" | "other";
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
