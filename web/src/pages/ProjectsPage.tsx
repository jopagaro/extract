import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { Project, ProjectCreate } from "../types";

// ── Icons ──────────────────────────────────────────────────────────────────

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M8 3v10M3 8h10" />
    </svg>
  );
}

function MineIcon() {
  return (
    <svg className="empty-state-icon" viewBox="0 0 52 52" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="26" cy="26" r="22" />
      <path d="M26 14v24M18 22l8-8 8 8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Status Badge ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: Project["status"] }) {
  const labels: Record<Project["status"], string> = {
    empty: "Empty",
    ingested: "Files Ready",
    analyzed: "Analyzed",
    error: "Error",
  };
  return <span className={`badge badge-${status}`}>{labels[status]}</span>;
}

// ── Create Modal ───────────────────────────────────────────────────────────

interface CreateModalProps {
  onClose: () => void;
  onCreate: (p: Project) => void;
}

function CreateModal({ onClose, onCreate }: CreateModalProps) {
  const [form, setForm] = useState<ProjectCreate>({
    name: "",
    description: "",
    commodity: "",
    study_type: "PEA",
  });
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  function set(field: keyof ProjectCreate, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    setLoading(true);
    try {
      const project = await createProject(form);
      onCreate(project);
      toast(`Project "${project.name}" created`, "success");
      onClose();
    } catch (err: unknown) {
      toast((err as Error).message ?? "Failed to create project", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-title">New Project</div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Project Name *</label>
            <input
              className="form-input"
              placeholder="e.g. Blackwater Gold Project"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              placeholder="Brief description of the project"
              value={form.description ?? ""}
              onChange={(e) => set("description", e.target.value)}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Primary Commodity</label>
              <input
                className="form-input"
                placeholder="Gold, Copper, Lithium..."
                value={form.commodity ?? ""}
                onChange={(e) => set("commodity", e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Study Type</label>
              <select
                className="form-select"
                value={form.study_type}
                onChange={(e) => set("study_type", e.target.value as ProjectCreate["study_type"])}
              >
                <option value="PEA">PEA</option>
                <option value="PFS">PFS</option>
                <option value="FS">FS</option>
                <option value="scoping">Scoping Study</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !form.name.trim()}>
              {loading ? <span className="spinner" /> : null}
              Create Project
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => toast("Could not load projects. Is the API server running?", "error"))
      .finally(() => setLoading(false));
  }, []);

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }


  return (
    <>
      <div className="page-header">
        <div>
          <h2>Projects</h2>
          <p>Each project is one mining asset — upload documents and run analysis</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <PlusIcon /> New Project
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "80px 0", color: "var(--text-secondary)" }}>
          <span className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <MineIcon />
          <h3>No projects yet</h3>
          <p>Create your first project to get started</p>
          <br />
          <button className="btn btn-primary" onClick={() => setShowCreate(true)} style={{ marginTop: 8 }}>
            <PlusIcon /> New Project
          </button>
        </div>
      ) : (
        <div className="card-grid">
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="project-card">
              <div className="project-card-header">
                <div>
                  <div className="project-card-name">{p.name}</div>
                  <div className="project-card-meta">
                    {p.commodity && <span>{p.commodity} · </span>}
                    {p.study_type}
                    {p.created_at && <span> · {formatDate(p.created_at)}</span>}
                  </div>
                </div>
                <StatusBadge status={p.status} />
              </div>
              {p.description && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>
                  {p.description}
                </div>
              )}
              <div className="project-card-stats">
                <div className="stat">
                  <div className="stat-value">{p.file_count}</div>
                  <div className="stat-label">Files</div>
                </div>
                <div className="stat">
                  <div className="stat-value">{p.run_count}</div>
                  <div className="stat-label">Runs</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreate={(p) => setProjects((prev) => [p, ...prev])}
        />
      )}
    </>
  );
}
