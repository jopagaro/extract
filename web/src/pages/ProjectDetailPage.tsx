import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

// ── Analysis step pills ─────────────────────────────────────────────────────

const ANALYSIS_STEPS = [
  { id: "loading",   label: "/loading",   order: 0, delay: 0 },
  { id: "extract",   label: "/extract",   order: 1, delay: 0 },
  { id: "geology",   label: "/geology",   order: 2, delay: 0 },
  { id: "economics", label: "/economics", order: 2, delay: 0.45 },
  { id: "risks",     label: "/risks",     order: 2, delay: 0.9 },
  { id: "report",    label: "/report",    order: 3, delay: 0 },
] as const;

const BACKEND_STEP_ORDER: Record<string, number> = {
  "queued":                    0,
  "Loading documents":         0,
  "Extracting project facts":  1,
  "Writing report sections":   2,
  "Finalising report":         3,
  "Complete":                  4,
};

function getStepState(
  step: typeof ANALYSIS_STEPS[number],
  currentStep: string,
  runStatus: string,
): "pending" | "active" | "done" {
  if (runStatus === "complete") return "done";
  if (runStatus === "failed") return "pending";
  const current = BACKEND_STEP_ORDER[currentStep] ?? 0;
  if (current > step.order) return "done";
  if (current === step.order) return "active";
  return "pending";
}

function AnalysisPills({ run }: { run: { step?: string; status: string } }) {
  const step = run.step ?? "queued";
  return (
    <div className="step-pills">
      {ANALYSIS_STEPS.map((s) => {
        const state = getStepState(s, step, run.status);
        return (
          <div key={s.id} className={`step-pill step-pill-${state}`}>
            <span className="step-pill-label">{s.label}</span>
            <div
              className="step-pill-fill"
              style={state === "active" ? { animationDelay: `${s.delay}s` } : undefined}
            >
              <span>{s.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
import {
  archiveProject,
  deleteFile,
  deleteRun,
  getProject,
  getRun,
  listFiles,
  listRuns,
  renameProject,
  startAnalysis,
  uploadFiles,
} from "../api/client";
import DropZone from "../components/shared/DropZone";
import { useToast } from "../components/shared/Toast";
import type { FileRecord, Project, RunStatus } from "../types";

// ── Icons ──────────────────────────────────────────────────────────────────

function FileIcon() {
  return (
    <svg className="file-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <circle cx="4" cy="10" r="1.5" />
      <circle cx="10" cy="10" r="1.5" />
      <circle cx="16" cy="10" r="1.5" />
    </svg>
  );
}

// ── Project Settings Dropdown ───────────────────────────────────────────────

function ProjectMenu({ onRename, onArchive }: { onRename: () => void; onArchive: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="btn btn-secondary btn-sm"
        onClick={() => setOpen((o) => !o)}
        title="Project settings"
      >
        <DotsIcon />
      </button>
      {open && (
        <div className="project-menu-dropdown">
          <button className="project-menu-item" onClick={() => { setOpen(false); onRename(); }}>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-8.793 8.793-3.536.707.707-3.535 8.794-8.793z" />
            </svg>
            Rename
          </button>
          <button className="project-menu-item" style={{ opacity: 0.5, cursor: "not-allowed" }} disabled>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
            </svg>
            Share <span style={{ fontSize: 10, marginLeft: 4, color: "var(--text-tertiary)" }}>soon</span>
          </button>
          <div className="project-menu-divider" />
          <button className="project-menu-item project-menu-item-danger" onClick={() => { setOpen(false); onArchive(); }}>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4zM3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
            </svg>
            Archive Project
          </button>
        </div>
      )}
    </div>
  );
}

// ── Rename Modal ────────────────────────────────────────────────────────────

function RenameModal({ current, onClose, onRename }: {
  current: string;
  onClose: () => void;
  onRename: (name: string) => void;
}) {
  const [name, setName] = useState(current);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || name.trim() === current) { onClose(); return; }
    setLoading(true);
    onRename(name.trim());
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-title">Rename Project</div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Project Name</label>
            <input
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? <span className="spinner" /> : null} Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

function RunBadge({ status }: { status: RunStatus["status"] }) {
  const label: Record<string, string> = {
    pending: "Queued",
    running: "Running",
    complete: "Complete",
    failed: "Failed",
  };
  const cls: Record<string, string> = {
    pending: "badge-pending",
    running: "badge-running",
    complete: "badge-complete",
    failed: "badge-error",
  };
  return <span className={`badge ${cls[status] ?? "badge-pending"}`}>{label[status] ?? status}</span>;
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<"files" | "runs">("files");
  const [showRename, setShowRename] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const id = projectId!;

  useEffect(() => {
    Promise.all([
      getProject(id),
      listFiles(id),
      listRuns(id),
    ]).then(([p, f, r]) => {
      setProject(p);
      setFiles(f);
      setRuns(r);
    }).catch(() => {
      toast("Could not load project", "error");
    });
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [id]);

  // Poll active run for status updates
  function startPolling(runId: string) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getRun(id, runId);
        setRuns((prev) => prev.map((r) => r.run_id === runId ? updated : r));
        if (updated.status === "complete" || updated.status === "failed") {
          clearInterval(pollRef.current!);
          setAnalyzing(false);
          if (updated.status === "complete") {
            toast("Analysis complete! View your report.", "success");
          } else {
            toast(`Analysis failed: ${updated.error ?? "Unknown error"}`, "error");
          }
        }
      } catch {
        clearInterval(pollRef.current!);
        setAnalyzing(false);
      }
    }, 2000);
  }

  async function handleUpload(newFiles: File[]) {
    setUploading(true);
    try {
      const result = await uploadFiles(id, newFiles);
      toast(`${result.queued.length} file(s) uploaded`, "success");
      if (result.skipped.length) toast(`${result.skipped.length} file(s) skipped (unsupported type)`, "info");
      const updated = await listFiles(id);
      setFiles(updated);
    } catch (err: unknown) {
      toast((err as Error).message ?? "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteFile(filename: string) {
    try {
      await deleteFile(id, filename);
      setFiles((prev) => prev.filter((f) => f.filename !== filename));
      toast(`Removed ${filename}`, "info");
    } catch {
      toast("Failed to remove file", "error");
    }
  }

  async function handleDeleteRun(runId: string) {
    try {
      await deleteRun(id, runId);
      setRuns((prev) => prev.filter((r) => r.run_id !== runId));
      toast("Run deleted", "info");
    } catch {
      toast("Failed to delete run", "error");
    }
  }

  async function handleRename(name: string) {
    try {
      await renameProject(id, name);
      setProject((p) => p ? { ...p, name } : p);
      toast(`Renamed to "${name}"`, "success");
    } catch {
      toast("Failed to rename project", "error");
    } finally {
      setShowRename(false);
    }
  }

  async function handleArchive() {
    if (!window.confirm(`Archive "${project?.name}"? It will be moved to the _archive folder and hidden from your projects list.`)) return;
    try {
      await archiveProject(id);
      toast(`"${project?.name}" archived`, "info");
      navigate("/projects");
    } catch {
      toast("Failed to archive project", "error");
    }
  }

  async function handleRunAnalysis() {
    if (files.length === 0) {
      toast("Upload files first before running analysis", "error");
      return;
    }
    setAnalyzing(true);
    try {
      const run = await startAnalysis(id);
      setRuns((prev) => [run, ...prev]);
      setActiveTab("runs");
      startPolling(run.run_id);
      toast("Analysis started — this may take 1–3 minutes", "info");
    } catch (err: unknown) {
      toast((err as Error).message ?? "Failed to start analysis", "error");
      setAnalyzing(false);
    }
  }

  if (!project) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <span className="spinner" style={{ width: 28, height: 28, color: "var(--text-tertiary)" }} />
      </div>
    );
  }

  const activeRun = runs.find((r) => r.status === "running" || r.status === "pending");
  const completeRuns = runs.filter((r) => r.status === "complete");

  return (
    <>
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/projects">Projects</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{project.name}</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <div>
          <h2>{project.name}</h2>
          <p>
            {project.commodity && <span>{project.commodity} · </span>}
            {project.study_type}
            {project.description && <span> · {project.description}</span>}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ProjectMenu onRename={() => setShowRename(true)} onArchive={handleArchive} />
          <button
            className="btn btn-primary btn-lg"
            onClick={handleRunAnalysis}
            disabled={analyzing || files.length === 0}
          >
            {analyzing ? (
              <><span className="spinner" /> Analyzing…</>
            ) : (
              <><PlayIcon /> Run Analysis</>
            )}
          </button>
        </div>
      </div>

      {showRename && (
        <RenameModal
          current={project.name}
          onClose={() => setShowRename(false)}
          onRename={handleRename}
        />
      )}

      {/* Analysis progress pills */}
      {activeRun && (
        <div style={{ marginBottom: 24 }}>
          <div className="run-panel">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Analysis in progress</span>
              <RunBadge status={activeRun.status} />
            </div>
            <AnalysisPills run={activeRun} />
          </div>
        </div>
      )}

      {/* Completed runs quick link */}
      {completeRuns.length > 0 && (
        <div className="card" style={{ marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 600 }}>{completeRuns.length} report{completeRuns.length > 1 ? "s" : ""} ready</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 3 }}>
              View the latest results or compare two runs side by side
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {completeRuns.length >= 2 && (
              <Link to={`/projects/${id}/compare`} className="btn btn-secondary">
                Compare
              </Link>
            )}
            <Link
              to={`/projects/${id}/report/${completeRuns[0].run_id}`}
              className="btn btn-primary"
            >
              View Report
            </Link>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab ${activeTab === "files" ? "active" : ""}`} onClick={() => setActiveTab("files")}>
          Files ({files.length})
        </button>
        <button className={`tab ${activeTab === "runs" ? "active" : ""}`} onClick={() => setActiveTab("runs")}>
          Runs ({runs.length})
        </button>
      </div>

      {/* Files tab */}
      {activeTab === "files" && (
        <>
          <DropZone onFiles={handleUpload} disabled={uploading} />

          {uploading && (
            <div style={{ textAlign: "center", padding: "16px 0", color: "var(--text-secondary)", fontSize: 13 }}>
              <span className="spinner" style={{ width: 16, height: 16 }} /> Uploading…
            </div>
          )}

          {files.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="section-header">
                <div className="section-title">File Library ({files.length})</div>
              </div>
              <div className="file-list">
                {files.map((f) => (
                  <div key={f.filename} className="file-row">
                    <FileIcon />
                    <span className="file-name">{f.filename}</span>
                    <span className="file-size">{formatBytes(f.size_bytes)}</span>
                    <button
                      className="btn-icon-only"
                      onClick={() => handleDeleteFile(f.filename)}
                      title="Remove file"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {files.length === 0 && !uploading && (
            <div style={{ textAlign: "center", padding: "20px", color: "var(--text-secondary)", fontSize: 13 }}>
              No files yet — drop your documents above to get started
            </div>
          )}
        </>
      )}

      {/* Runs tab */}
      {activeTab === "runs" && (
        <>
          {runs.length === 0 ? (
            <div className="empty-state">
              <h3>No runs yet</h3>
              <p>Upload files and click "Run Analysis" to generate your first report</p>
            </div>
          ) : (
            <div className="run-panel">
              {runs.map((r) => (
                <div key={r.run_id} className="run-row">
                  <RunBadge status={r.status} />
                  <span className="run-id">{r.run_id}</span>
                  <span className="run-step">{r.error ?? r.step ?? ""}</span>
                  <span className="run-time">
                    {r.completed_at
                      ? new Date(r.completed_at).toLocaleString()
                      : r.started_at
                      ? new Date(r.started_at).toLocaleString()
                      : ""}
                  </span>
                  {r.status === "complete" && (
                    <Link
                      to={`/projects/${id}/report/${r.run_id}`}
                      className="btn btn-secondary btn-sm"
                    >
                      View Report
                    </Link>
                  )}
                  {r.status !== "running" && r.status !== "pending" && (
                    <button
                      className="btn-icon-only"
                      onClick={() => handleDeleteRun(r.run_id)}
                      title="Delete run"
                    >
                      <TrashIcon />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
