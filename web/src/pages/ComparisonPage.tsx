import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport, listRuns } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { ReportContent, RunStatus } from "../types";

// ---------------------------------------------------------------------------
// Diff engine
// ---------------------------------------------------------------------------

type DiffStatus = "added" | "removed" | "changed" | "unchanged";

interface DiffRow {
  section: string;
  sectionTitle: string;
  key: string;
  valueA: unknown;
  valueB: unknown;
  status: DiffStatus;
}

function humanTitle(key: string) {
  return key
    .replace(/^\d+_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function flattenScalars(obj: unknown, prefix = ""): Record<string, unknown> {
  if (typeof obj !== "object" || obj === null || Array.isArray(obj)) return {};
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      out[path] = v;
    } else if (typeof v === "object" && v !== null && !Array.isArray(v)) {
      Object.assign(out, flattenScalars(v, path));
    }
  }
  return out;
}

function computeDiff(a: ReportContent | null, b: ReportContent | null): DiffRow[] {
  if (!a || !b) return [];
  const rows: DiffRow[] = [];

  const allSections = Array.from(
    new Set([...Object.keys(a.sections), ...Object.keys(b.sections)])
  ).sort();

  for (const section of allSections) {
    const title = humanTitle(section);
    const secA = a.sections[section];
    const secB = b.sections[section];

    if (secA === undefined && secB !== undefined) {
      rows.push({ section, sectionTitle: title, key: "(section)", valueA: null, valueB: "(present)", status: "added" });
      continue;
    }
    if (secA !== undefined && secB === undefined) {
      rows.push({ section, sectionTitle: title, key: "(section)", valueA: "(present)", valueB: null, status: "removed" });
      continue;
    }

    // Flatten scalars from both sides
    const flatA = flattenScalars(secA);
    const flatB = flattenScalars(secB);
    const allKeys = Array.from(new Set([...Object.keys(flatA), ...Object.keys(flatB)])).sort();

    let sectionHadChanges = false;
    for (const key of allKeys) {
      const va = flatA[key];
      const vb = flatB[key];
      let status: DiffStatus = "unchanged";

      if (va === undefined) status = "added";
      else if (vb === undefined) status = "removed";
      else if (String(va) !== String(vb)) status = "changed";

      if (status !== "unchanged") {
        sectionHadChanges = true;
        rows.push({
          section,
          sectionTitle: title,
          key: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
          valueA: va ?? null,
          valueB: vb ?? null,
          status,
        });
      }
    }

    // If the section exists in both but has no changed scalars, check prose length change
    if (!sectionHadChanges) {
      const textA = JSON.stringify(secA);
      const textB = JSON.stringify(secB);
      if (textA !== textB) {
        rows.push({
          section,
          sectionTitle: title,
          key: "(narrative text)",
          valueA: `${Math.round(textA.length / 5)} words`,
          valueB: `${Math.round(textB.length / 5)} words`,
          status: "changed",
        });
      }
    }
  }

  return rows;
}

// ---------------------------------------------------------------------------
// Side-by-side section renderers (kept from original)
// ---------------------------------------------------------------------------

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

function SectionContent({ sectionKey, content }: { sectionKey: string; content: unknown }) {
  if (sectionKey === "00_data_sources") return <DataSourcesSection data={content as Record<string, unknown>} />;
  if (typeof content === "object" && content !== null && !Array.isArray(content))
    return <ProseSection data={content as Record<string, unknown>} />;
  if (typeof content === "string")
    return <div className="report-prose-block"><p>{content}</p></div>;
  return <pre style={{ fontSize: 11, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
}

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
          const title = humanTitle(key);
          return (
            <div key={key} className="compare-section">
              <div className="compare-section-title">{title}</div>
              <SectionContent sectionKey={key} content={content} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Diff view
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<DiffStatus, { bg: string; text: string; badge: string }> = {
  changed: { bg: "rgba(245,158,11,0.07)", text: "var(--text-primary)", badge: "rgba(245,158,11,0.15)" },
  added:   { bg: "rgba(34,197,94,0.07)",  text: "var(--text-primary)", badge: "rgba(34,197,94,0.15)" },
  removed: { bg: "rgba(220,53,53,0.07)",  text: "var(--text-primary)", badge: "rgba(220,53,53,0.15)" },
  unchanged: { bg: "transparent", text: "var(--text-secondary)", badge: "transparent" },
};

const STATUS_LABELS: Record<DiffStatus, string> = {
  changed: "Changed",
  added: "Added",
  removed: "Removed",
  unchanged: "",
};

function DiffView({
  rows,
  runAId,
  runBId,
}: {
  rows: DiffRow[];
  runAId: string;
  runBId: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="empty-state" style={{ marginTop: 40 }}>
        <h3>No differences found</h3>
        <p>These two runs produced identical output — the analysis is consistent.</p>
      </div>
    );
  }

  // Group by section
  const sections = Array.from(new Set(rows.map((r) => r.section)));

  const changedCount = rows.filter((r) => r.status === "changed").length;
  const addedCount   = rows.filter((r) => r.status === "added").length;
  const removedCount = rows.filter((r) => r.status === "removed").length;

  return (
    <div>
      {/* Summary chips */}
      <div style={{ display: "flex", gap: 10, marginBottom: 24, flexWrap: "wrap" }}>
        <div className="card" style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{rows.length}</span>
          <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>total differences</span>
        </div>
        {changedCount > 0 && (
          <div className="card" style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: "#d97706" }}>{changedCount}</span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>changed</span>
          </div>
        )}
        {addedCount > 0 && (
          <div className="card" style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: "#16a34a" }}>{addedCount}</span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>added</span>
          </div>
        )}
        {removedCount > 0 && (
          <div className="card" style={{ padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: "#dc3535" }}>{removedCount}</span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>removed</span>
          </div>
        )}
      </div>

      {/* Diff table per section */}
      {sections.map((section) => {
        const sectionRows = rows.filter((r) => r.section === section);
        const title = sectionRows[0]?.sectionTitle ?? humanTitle(section);
        return (
          <div key={section} style={{ marginBottom: 28 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              color: "var(--text-tertiary)",
              marginBottom: 8,
              paddingBottom: 6,
              borderBottom: "1px solid var(--border)",
            }}>
              {title}
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: "6px 10px", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, width: "28%" }}>Field</th>
                  <th style={{ textAlign: "left", padding: "6px 10px", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, width: "30%" }}>
                    Run A · <span style={{ fontFamily: "monospace", fontSize: 10 }}>{runAId.slice(-8)}</span>
                  </th>
                  <th style={{ textAlign: "left", padding: "6px 10px", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 600, width: "30%" }}>
                    Run B · <span style={{ fontFamily: "monospace", fontSize: 10 }}>{runBId.slice(-8)}</span>
                  </th>
                  <th style={{ width: "12%" }} />
                </tr>
              </thead>
              <tbody>
                {sectionRows.map((row, i) => {
                  const colors = STATUS_COLORS[row.status];
                  return (
                    <tr key={i} style={{ background: colors.bg, borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "9px 10px", fontWeight: 500, color: "var(--text-primary)", verticalAlign: "top" }}>
                        {row.key}
                      </td>
                      <td style={{ padding: "9px 10px", color: row.status === "added" ? "var(--text-tertiary)" : "var(--text-primary)", verticalAlign: "top" }}>
                        {row.valueA === null || row.valueA === undefined ? (
                          <span style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>—</span>
                        ) : (
                          <span style={{
                            textDecoration: row.status === "changed" ? "line-through" : "none",
                            opacity: row.status === "changed" ? 0.5 : 1,
                          }}>
                            {truncate(String(row.valueA), 120)}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "9px 10px", color: row.status === "removed" ? "var(--text-tertiary)" : "var(--text-primary)", verticalAlign: "top" }}>
                        {row.valueB === null || row.valueB === undefined ? (
                          <span style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>—</span>
                        ) : (
                          <span style={{ fontWeight: row.status === "changed" ? 600 : 400 }}>
                            {truncate(String(row.valueB), 120)}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "9px 10px", textAlign: "right" }}>
                        <span style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "2px 7px",
                          borderRadius: 4,
                          background: colors.badge,
                          color: row.status === "changed" ? "#d97706" : row.status === "added" ? "#16a34a" : "#dc3535",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}>
                          {STATUS_LABELS[row.status]}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

function truncate(s: string, max: number) {
  if (s.length <= max) return s;
  return s.slice(0, max) + "…";
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

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
  const [viewMode, setViewMode] = useState<"side-by-side" | "diff">("diff");

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

  const diffRows = useMemo(
    () => computeDiff(leftReport, rightReport),
    [leftReport, rightReport],
  );

  const loading = leftLoading || rightLoading;

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
            {runs.length} completed run{runs.length !== 1 ? "s" : ""} — select two to compare
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
          <Link to={`/projects/${id}`} className="btn btn-primary" style={{ marginTop: 16 }}>
            Run Analysis
          </Link>
        </div>
      ) : (
        <>
          {/* Run selectors + view toggle */}
          <div style={{ display: "flex", alignItems: "flex-end", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
            <div className="compare-selector-group">
              <label className="form-label">Run A</label>
              <select className="form-select" value={leftRunId} onChange={(e) => setLeftRunId(e.target.value)}>
                <option value="">— Select run —</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}{r.completed_at ? ` · ${new Date(r.completed_at).toLocaleDateString()}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="compare-vs-label">vs</div>

            <div className="compare-selector-group">
              <label className="form-label">Run B</label>
              <select className="form-select" value={rightRunId} onChange={(e) => setRightRunId(e.target.value)}>
                <option value="">— Select run —</option>
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}{r.completed_at ? ` · ${new Date(r.completed_at).toLocaleDateString()}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginLeft: "auto", display: "flex", gap: 0, borderRadius: 6, overflow: "hidden", border: "1px solid var(--border)" }}>
              <button
                onClick={() => setViewMode("diff")}
                style={{
                  padding: "7px 16px",
                  fontSize: 13,
                  fontWeight: viewMode === "diff" ? 600 : 400,
                  background: viewMode === "diff" ? "var(--accent)" : "transparent",
                  color: viewMode === "diff" ? "#fff" : "var(--text-secondary)",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Diff
              </button>
              <button
                onClick={() => setViewMode("side-by-side")}
                style={{
                  padding: "7px 16px",
                  fontSize: 13,
                  fontWeight: viewMode === "side-by-side" ? 600 : 400,
                  background: viewMode === "side-by-side" ? "var(--accent)" : "transparent",
                  color: viewMode === "side-by-side" ? "#fff" : "var(--text-secondary)",
                  border: "none",
                  borderLeft: "1px solid var(--border)",
                  cursor: "pointer",
                }}
              >
                Side by side
              </button>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)" }}>
              <span className="spinner" style={{ width: 24, height: 24 }} />
            </div>
          )}

          {/* Diff view */}
          {!loading && viewMode === "diff" && leftReport && rightReport && (
            <DiffView rows={diffRows} runAId={leftRunId} runBId={rightRunId} />
          )}

          {/* Side-by-side view */}
          {!loading && viewMode === "side-by-side" && (
            <div className="compare-view">
              <ReportPanel projectId={id} runId={leftRunId} report={leftReport} loading={leftLoading} />
              <div className="compare-divider" />
              <ReportPanel projectId={id} runId={rightRunId} report={rightReport} loading={rightLoading} />
            </div>
          )}
        </>
      )}
    </>
  );
}
