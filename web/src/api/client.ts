// API client — thin wrapper around the FastAPI backend

import type {
  FileRecord,
  IngestResponse,
  Project,
  ProjectCreate,
  ReportContent,
  RunStatus,
} from "../types";

const BASE = "/api";

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

// ── Analysis ────────────────────────────────────────────────────────────────

export async function startAnalysis(projectId: string): Promise<RunStatus> {
  return request(`/projects/${projectId}/analyze`, {
    method: "POST",
    body: JSON.stringify({ force: false }),
  });
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

export function exportUrl(
  projectId: string,
  runId: string,
  format: "json" | "md" | "txt" = "md"
): string {
  return `${BASE}/projects/${projectId}/reports/${runId}/export?format=${format}`;
}
