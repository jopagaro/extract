import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { listFiles, listProjects } from "../../api/client";
import type { FileRecord, Project } from "../../types";

// ── Icons ───────────────────────────────────────────────────────────────────

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="11" height="11" viewBox="0 0 20 20" fill="currentColor"
      style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.15s ease", flexShrink: 0 }}
    >
      <path fillRule="evenodd" d="M7.293 4.293a1 1 0 011.414 0l5 5a1 1 0 010 1.414l-5 5a1 1 0 01-1.414-1.414L11.586 10 7.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

function FileSmIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 20 20" fill="currentColor" style={{ flexShrink: 0, opacity: 0.5 }}>
      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}

// ── Project Row with expandable file list ────────────────────────────────────

function ProjectRow({
  project,
  isActive,
  onExpand,
  files,
}: {
  project: Project;
  isActive: boolean;
  onExpand: (id: string) => void;
  files: FileRecord[] | undefined;
}) {
  const [expanded, setExpanded] = useState(isActive);

  useEffect(() => {
    if (isActive && !expanded) {
      setExpanded(true);
      if (files === undefined) onExpand(project.id);
    }
  }, [isActive]);

  function toggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    const next = !expanded;
    setExpanded(next);
    if (next && files === undefined) onExpand(project.id);
  }

  return (
    <div className="sidebar-project-group">
      <div className={`sidebar-project-row ${isActive ? "active" : ""}`}>
        <button className="sidebar-chevron-btn" onClick={toggle} tabIndex={-1}>
          <ChevronIcon open={expanded} />
        </button>
        <Link to={`/projects/${project.id}`} className="sidebar-project-name">
          <FolderIcon />
          <span>{project.name}</span>
        </Link>
        {project.file_count > 0 && (
          <span className="sidebar-count">{project.file_count}</span>
        )}
      </div>

      {expanded && (
        <div className="sidebar-file-tree">
          {files === undefined ? (
            <div className="sidebar-file-placeholder">Loading…</div>
          ) : files.length === 0 ? (
            <div className="sidebar-file-placeholder">No files yet</div>
          ) : (
            files.map((f) => (
              <div key={f.filename} className="sidebar-file-row" title={f.filename}>
                <FileSmIcon />
                <span className="sidebar-file-name">{f.filename}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ── Layout ──────────────────────────────────────────────────────────────────

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [projects, setProjects] = useState<Project[]>([]);
  const [fileCache, setFileCache] = useState<Record<string, FileRecord[]>>({});
  const hasFetchedRef = useRef(false);

  // Extract active project ID from URL
  const match = location.pathname.match(/^\/projects\/([^/]+)/);
  const activeProjectId = match?.[1] ?? null;
  const isReportRoute = /\/report\//.test(location.pathname);

  // Fetch projects list — refresh whenever we land on /projects
  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => {});
  }, [location.pathname === "/projects" ? location.pathname : "static"]);

  // Fetch files for the active project automatically
  useEffect(() => {
    if (activeProjectId && fileCache[activeProjectId] === undefined) {
      loadFiles(activeProjectId);
    }
  }, [activeProjectId]);

  function loadFiles(projectId: string) {
    listFiles(projectId)
      .then((files) => setFileCache((prev) => ({ ...prev, [projectId]: files })))
      .catch(() => setFileCache((prev) => ({ ...prev, [projectId]: [] })));
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Extract</h1>
          <p>Mining Project Intelligence</p>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Projects</div>

          {projects.length === 0 ? (
            <div className="sidebar-empty">No projects yet</div>
          ) : (
            projects.map((p) => (
              <ProjectRow
                key={p.id}
                project={p}
                isActive={activeProjectId === p.id}
                onExpand={loadFiles}
                files={fileCache[p.id]}
              />
            ))
          )}

          <Link to="/projects" className="sidebar-new-btn">
            <span style={{ fontSize: 16, lineHeight: 1, marginRight: 4 }}>+</span> New Project
          </Link>

          <div className="sidebar-section-label" style={{ marginTop: 20 }}>Tools</div>
          <Link
            to="/portfolio/compare"
            className={`sidebar-bottom-link sidebar-tool-link ${location.pathname.startsWith("/portfolio") ? "active" : ""}`}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" />
              <path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z" />
            </svg>
            Portfolio
          </Link>
        </nav>

        <div className="sidebar-bottom">
          <Link
            to="/tools"
            className={`sidebar-bottom-link ${location.pathname === "/tools" ? "active" : ""}`}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
            </svg>
            Tools
          </Link>
          <Link
            to="/settings"
            className={`sidebar-bottom-link ${location.pathname === "/settings" ? "active" : ""}`}
          >
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
            </svg>
            Settings
          </Link>
        </div>
      </aside>

      <main className={`main-content${isReportRoute ? " main-content--report" : ""}`}>{children}</main>
    </div>
  );
}
