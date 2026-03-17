// API client — thin wrapper around the FastAPI backend
const BASE = "/api";
async function request(path, init) {
    const res = await fetch(`${BASE}${path}`, {
        headers: { "Content-Type": "application/json", ...init?.headers },
        ...init,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Request failed");
    }
    if (res.status === 204)
        return undefined;
    return res.json();
}
// ── Projects ────────────────────────────────────────────────────────────────
export async function listProjects() {
    const data = await request("/projects");
    return data.projects;
}
export async function createProject(body) {
    return request("/projects", {
        method: "POST",
        body: JSON.stringify(body),
    });
}
export async function getProject(id) {
    return request(`/projects/${id}`);
}
export async function deleteProject(id) {
    return request(`/projects/${id}`, { method: "DELETE" });
}
// ── Files ───────────────────────────────────────────────────────────────────
export async function listFiles(projectId) {
    const data = await request(`/projects/${projectId}/files`);
    return data.files;
}
export async function uploadFiles(projectId, files) {
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
export async function deleteFile(projectId, filename) {
    return request(`/projects/${projectId}/files/${encodeURIComponent(filename)}`, {
        method: "DELETE",
    });
}
// ── Analysis ────────────────────────────────────────────────────────────────
export async function startAnalysis(projectId) {
    return request(`/projects/${projectId}/analyze`, {
        method: "POST",
        body: JSON.stringify({ force: false }),
    });
}
export async function listRuns(projectId) {
    const data = await request(`/projects/${projectId}/runs`);
    return data.runs;
}
export async function getRun(projectId, runId) {
    return request(`/projects/${projectId}/runs/${runId}`);
}
// ── Reports ─────────────────────────────────────────────────────────────────
export async function getReport(projectId, runId) {
    return request(`/projects/${projectId}/reports/${runId}`);
}
export function exportUrl(projectId, runId, format = "md") {
    return `${BASE}/projects/${projectId}/reports/${runId}/export?format=${format}`;
}
