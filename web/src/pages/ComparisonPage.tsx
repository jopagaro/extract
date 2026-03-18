import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport, listRuns } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { ReportContent, RunStatus } from "../types";

// ── Reuse section renderers from ReportPage ─────────────────────────────────

function DataSourcesSection({ data }: { data: Record<string, unknown> }) {
  const files = (data.source_files as string[]) ?? [];
  return (
    <div>
      <div className="report-notice">{String(data.notice ?? "")}</div>
      {files.length > 0 && (
        <div className="report-file-list">
          {files.map((f, i) => (
            <div key={i} className="report-file-row">
              <span className="report-file-check">✓</span>
              {f}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ListBlock({ items, title }: { items: unknown[]; title?: string }) {
  if (!items.length) return null;
  if (typeof items[0] === "object" && items[0] !== null) {
    const cols = Object.keys(items[0] as object);
    return (
      <div style={{ marginTop: 14 }}>
        {title && <div className="report-sub-label">{title}</div>}
        <div style={{ overflowX: "auto" }}>
          <table className="report-table">
            <thead>
              <tr>{cols.map((c) => <th key={c}>{c.replace(/_/g, " ")}</th>)}</tr>
            </thead>
            <tbody>
              {(items as Record<string, unknown>[]).map((row, i) => (
                <tr key={i}>
                  {cols.map((c) => (
                    <td key={c}>{row[c] === null || row[c] === undefined ? "—" : String(row[c])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
  return (
    <div style={{ marginTop: 14 }}>
      {title && <div className="report-sub-label">{title}</div>}
      <ul className="report-bullet-list">
        {items.map((item, i) => (
          <li key={i}><span className="report-bullet">—</span><span>{String(item)}</span></li>
        ))}
      </ul>
    </div>
  );
}

function ProseSection({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  const prose = entries.filter(([, v]) => typeof v === "string" && (v as string).length > 60);
  const lists = entries.filter(([, v]) => Array.isArray(v) && (v as unknown[]).length > 0);
  const scalars = entries.filter(([k]) =>
    !prose.find(([pk]) => pk === k) && !lists.find(([lk]) => lk === k)
  );
  const isSingleProse = prose.length === 1 && lists.length === 0 && scalars.length === 0;

  return (
    <div className="report-prose-block">
      {prose.map(([k, v]) => (
        <div key={k} className="report-prose-para">
          {!isSingleProse && prose.length > 1 && (
            <div className="report-para-label">{k.replace(/_/g, " ")}</div>
          )}
          <p>{String(v)}</p>
        </div>
      ))}
      {lists.map(([k, v]) => (
        <ListBlock
          key={k}
          items={v as unknown[]}
          title={lists.length > 1 || prose.length > 0
            ? k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
            : undefined}
        />
      ))}
      {scalars.length > 0 && (
        <div className="report-scalar-row">
          {scalars.map(([k, v]) => (
            <div key={k} className="report-scalar-chip">
              <span className="report-scalar-label">
                {k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <span className="report-scalar-value">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Section metadata ─────────────────────────────────────────────────────────

const SECTION_META: Record<string, { title: string }> = {
  "00_data_sources": { title: "Data Sources" },
  "01_project_facts": { title: "Project Overview" },
  "02_executive_summary": { title: "Executive Summary" },
  "03_geology": { title: "Geology" },
  "04_economics": { title: "Economics" },
  "05_risks": { title: "Risks & Uncertainties" },
};

function SectionContent({ sectionKey, content }: { sectionKey: string; content: unknown }) {
  if (sectionKey === "00_data_sources") return <DataSourcesSection data={content as Record<string, unknown>} />;
  if (typeof content === "object" && content !== null && !Array.isArray(content))
    return <ProseSection data={content as Record<string, unknown>} />;
  if (typeof content === "string")
    return <div className="report-prose-block"><p>{content}</p></div>;
  return <pre style={{ fontSize: 11, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
}

// ── Report Panel ─────────────────────────────────────────────────────────────

function ReportPanel({
  projectId,
  runId,
  report,
  loading,
}: {
  projectId: string;
  runId: string;
  report: ReportContent | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="compare-panel compare-panel-loading">
        <span className="spinner" style={{ width: 24, height: 24, color: "var(--text-tertiary)" }} />
      </div>
    );
  }
  if (!report) {
    return (
      <div className="compare-panel compare-panel-empty">
        <p>Select a run above to view its report</p>
      </div>
    );
  }

  const sections = Object.entries(report.sections).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="compare-panel">
      <div className="compare-panel-header">
        <div className="compare-run-id">{runId}</div>
        <Link
          to={`/projects/${projectId}/report/${runId}`}
          className="btn btn-secondary btn-sm"
          target="_blank"
        >
          Full Report ↗
        </Link>
      </div>

      <div className="compare-panel-body">
        {sections.map(([key, content]) => {
          const meta = SECTION_META[key] ?? {
            title: key.replace(/^\d+_/, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          };
          return (
            <div key={key} className="compare-section">
              <div className="compare-section-title">{meta.title}</div>
              <SectionContent sectionKey={key} content={content} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ComparisonPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { toast } = useToast();
  const id = projectId!;

  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [leftRunId, setLeftRunId] = useState("");
  const [rightRunId, setRightRunId] = useState("");
  const [leftReport, setLeftReport] = useState<ReportContent | null>(null);
  const [rightReport, setRightReport] = useState<ReportContent | null>(null);
  const [leftLoading, setLeftLoading] = useState(false);
  const [rightLoading, setRightLoading] = useState(false);

  const projectName = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  useEffect(() => {
    listRuns(id)
      .then((r) => {
        const complete = r.filter((x) => x.status === "complete");
        setRuns(complete);
        if (complete.length >= 1) setLeftRunId(complete[0].run_id);
        if (complete.length >= 2) setRightRunId(complete[1].run_id);
      })
      .catch(() => toast("Could not load runs", "error"));
  }, [id]);

  useEffect(() => {
    if (!leftRunId) { setLeftReport(null); return; }
    setLeftLoading(true);
    setLeftReport(null);
    getReport(id, leftRunId)
      .then(setLeftReport)
      .catch(() => toast("Could not load report", "error"))
      .finally(() => setLeftLoading(false));
  }, [leftRunId]);

  useEffect(() => {
    if (!rightRunId) { setRightReport(null); return; }
    setRightLoading(true);
    setRightReport(null);
    getReport(id, rightRunId)
      .then(setRightReport)
      .catch(() => toast("Could not load report", "error"))
      .finally(() => setRightLoading(false));
  }, [rightRunId]);

  return (
    <>
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/projects">Projects</Link>
        <span className="breadcrumb-sep">/</span>
        <Link to={`/projects/${id}`}>{projectName}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Compare</span>
      </div>

      <div className="page-header" style={{ marginBottom: 24 }}>
        <div>
          <h2>Compare Runs</h2>
          <p>
            {runs.length} completed run{runs.length !== 1 ? "s" : ""} — select two to view side by side
          </p>
        </div>
        <Link to={`/projects/${id}`} className="btn btn-secondary btn-sm">
          ← Back to Project
        </Link>
      </div>

      {runs.length < 2 ? (
        <div className="empty-state">
          <h3>Not enough runs to compare</h3>
          <p>You need at least two completed runs to use the comparison view.</p>
          <br />
          <Link to={`/projects/${id}`} className="btn btn-primary" style={{ marginTop: 8 }}>
            Run Analysis
          </Link>
        </div>
      ) : (
        <>
          {/* Run selectors */}
          <div className="compare-selectors">
            <div className="compare-selector-group">
              <label className="form-label">Run A</label>
              <select
                className="form-select"
                value={leftRunId}
                onChange={(e) => setLeftRunId(e.target.value)}
              >
                <option value="">— Select run —</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}
                    {r.completed_at ? ` · ${new Date(r.completed_at).toLocaleDateString()}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="compare-vs-label">vs</div>

            <div className="compare-selector-group">
              <label className="form-label">Run B</label>
              <select
                className="form-select"
                value={rightRunId}
                onChange={(e) => setRightRunId(e.target.value)}
              >
                <option value="">— Select run —</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}
                    {r.completed_at ? ` · ${new Date(r.completed_at).toLocaleDateString()}` : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Side-by-side panels */}
          <div className="compare-view">
            <ReportPanel
              projectId={id}
              runId={leftRunId}
              report={leftReport}
              loading={leftLoading}
            />
            <div className="compare-divider" />
            <ReportPanel
              projectId={id}
              runId={rightRunId}
              report={rightReport}
              loading={rightLoading}
            />
          </div>
        </>
      )}
    </>
  );
}
