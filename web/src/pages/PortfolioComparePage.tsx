import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { comparePortfolio, getPortfolioProjects, type ProjectMetrics } from "../api/client";
import { useToast } from "../components/shared/Toast";

// ---------------------------------------------------------------------------
// Metric definitions — what rows appear in the comparison matrix
// ---------------------------------------------------------------------------

type MetricGroup = {
  group: string;
  metrics: Array<{
    label: string;
    key: keyof ProjectMetrics;
    format: (v: unknown, row?: ProjectMetrics) => string;
    higherIsBetter?: boolean; // true = green for max; false = green for min; undefined = no highlight
    unit?: string;
  }>;
};

const METRIC_GROUPS: MetricGroup[] = [
  {
    group: "Project",
    metrics: [
      { label: "Commodity",     key: "commodity",    format: s => s ? String(s) : "—" },
      { label: "Study Stage",   key: "study_type",   format: s => s ? String(s) : "—" },
      { label: "Jurisdiction",  key: "jurisdiction", format: s => s ? String(s) : "—" },
      { label: "Operator",      key: "operator",     format: s => s ? String(s) : "—" },
      { label: "Mine Life",     key: "mine_life_years", format: v => v != null ? `${v} yrs` : "—", higherIsBetter: true },
    ],
  },
  {
    group: "Resources",
    metrics: [
      { label: "Total Resource", key: "total_resource_mt", format: v => v != null ? `${(v as number).toLocaleString()} Mt` : "—", higherIsBetter: true },
      { label: "M+I Tonnes",     key: "mi_resource_mt",    format: v => v != null ? `${(v as number).toLocaleString()} Mt` : "—", higherIsBetter: true },
      { label: "Inferred %",     key: "inferred_pct",      format: v => v != null ? `${v}%` : "—", higherIsBetter: false },
      { label: "Primary Grade",  key: "primary_grade",     format: (v, p) => v != null ? `${v} ${(p as ProjectMetrics).grade_unit ?? ""}`.trim() : "—", higherIsBetter: true },
      { label: "Contained Metal",key: "total_contained",   format: (v, p) => v != null ? `${v} ${(p as ProjectMetrics).metal_unit ?? ""}`.trim() : "—", higherIsBetter: true },
    ],
  },
  {
    group: "Economics",
    metrics: [
      { label: "NPV (M USD)",    key: "npv_musd",           format: v => v != null ? `$${(v as number).toLocaleString()}M` : "—", higherIsBetter: true },
      { label: "IRR",            key: "irr_pct",            format: v => v != null ? `${v}%` : "—", higherIsBetter: true },
      { label: "Payback",        key: "payback_years",      format: v => v != null ? `${v} yrs` : "—", higherIsBetter: false },
      { label: "Initial Capex",  key: "initial_capex_musd", format: v => v != null ? `$${(v as number).toLocaleString()}M` : "—", higherIsBetter: false },
      { label: "AISC ($/oz)",    key: "aisc_per_oz",        format: v => v != null ? `$${(v as number).toLocaleString()}` : "—", higherIsBetter: false },
      { label: "Opex ($/t)",     key: "opex_per_tonne",     format: v => v != null ? `$${v}` : "—", higherIsBetter: false },
    ],
  },
  {
    group: "Encumbrances",
    metrics: [
      { label: "NSR / GR Burden", key: "nsr_burden_pct", format: v => v != null ? `${v}%` : "—", higherIsBetter: false },
      { label: "Stream",          key: "has_stream",      format: v => v ? "Yes" : "No" },
    ],
  },
  {
    group: "Coverage",
    metrics: [
      { label: "Documents",   key: "file_count",        format: v => String(v ?? 0), higherIsBetter: true },
      { label: "Runs",        key: "run_count",          format: v => String(v ?? 0) },
      { label: "Analyst Notes", key: "notes_count",     format: v => String(v ?? 0) },
      { label: "Comparables", key: "comparables_count", format: v => String(v ?? 0) },
    ],
  },
];

// ---------------------------------------------------------------------------
// Highlight helpers
// ---------------------------------------------------------------------------

function getHighlights(
  projects: ProjectMetrics[],
  key: keyof ProjectMetrics,
  higherIsBetter: boolean,
): Map<string, "best" | "worst"> {
  const vals = projects.map(p => ({ id: p.project_id, val: p[key] as number | null }))
    .filter(x => x.val != null && typeof x.val === "number") as { id: string; val: number }[];
  if (vals.length < 2) return new Map();
  const sorted = [...vals].sort((a, b) => a.val - b.val);
  const map = new Map<string, "best" | "worst">();
  const best = higherIsBetter ? sorted[sorted.length - 1] : sorted[0];
  const worst = higherIsBetter ? sorted[0] : sorted[sorted.length - 1];
  if (best.val !== worst.val) {
    map.set(best.id, "best");
    map.set(worst.id, "worst");
  }
  return map;
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

type PortfolioProject = { id: string; name: string; commodity?: string; study_type?: string; status?: string };

export default function PortfolioComparePage() {
  const { toast } = useToast();
  const [allProjects, setAllProjects] = useState<PortfolioProject[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [comparison, setComparison] = useState<ProjectMetrics[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    getPortfolioProjects()
      .then((ps) => {
        setAllProjects(ps);
        // Auto-select first 3
        setSelected(new Set(ps.slice(0, 3).map(p => p.id)));
      })
      .catch(() => toast("Could not load projects", "error"))
      .finally(() => setInitialLoading(false));
  }, []);

  function toggleProject(id: string) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    // Clear comparison when selection changes
    setComparison([]);
  }

  async function handleCompare() {
    if (selected.size < 2) {
      toast("Select at least 2 projects to compare", "error");
      return;
    }
    setLoading(true);
    try {
      const results = await comparePortfolio(Array.from(selected));
      setComparison(results);
    } catch {
      toast("Failed to load comparison", "error");
    } finally {
      setLoading(false);
    }
  }

  const studyBadgeColor: Record<string, string> = {
    PEA: "#6366f1", PFS: "#0891b2", FS: "#16a34a", scoping: "#d97706", other: "#6b7280",
  };

  return (
    <>
      <div className="breadcrumb">
        <Link to="/projects">Projects</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Portfolio Compare</span>
      </div>

      <div className="page-header" style={{ marginBottom: 24 }}>
        <div>
          <h2>Portfolio Comparison</h2>
          <p>Select projects and compare them side by side across all key metrics</p>
        </div>
        <Link to="/projects" className="btn btn-secondary btn-sm">← Projects</Link>
      </div>

      {initialLoading ? (
        <div style={{ textAlign: "center", padding: "60px 0" }}>
          <span className="spinner" style={{ width: 24, height: 24, color: "var(--text-tertiary)" }} />
        </div>
      ) : allProjects.length < 2 ? (
        <div className="empty-state">
          <h3>Not enough projects</h3>
          <p>You need at least two projects to use portfolio comparison.</p>
          <Link to="/projects" className="btn btn-primary" style={{ marginTop: 16 }}>
            Create a Project
          </Link>
        </div>
      ) : (
        <>
          {/* Project selector */}
          <div className="card" style={{ padding: "18px 20px", marginBottom: 24 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
              Select projects to compare
              <span style={{ fontWeight: 400, color: "var(--text-tertiary)", fontSize: 12, marginLeft: 8 }}>
                ({selected.size} selected — select 2 or more)
              </span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {allProjects.map(p => {
                const isSelected = selected.has(p.id);
                const color = studyBadgeColor[p.study_type ?? "other"] ?? "#6b7280";
                return (
                  <button
                    key={p.id}
                    onClick={() => toggleProject(p.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 14px",
                      borderRadius: 8,
                      border: `2px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                      background: isSelected ? "rgba(44,74,62,0.06)" : "transparent",
                      cursor: "pointer",
                      fontSize: 13,
                      fontWeight: isSelected ? 600 : 400,
                      color: "var(--text-primary)",
                      transition: "all 0.15s",
                    }}
                  >
                    <span style={{
                      width: 8, height: 8, borderRadius: "50%",
                      background: isSelected ? "var(--accent)" : "var(--border)",
                      flexShrink: 0,
                    }} />
                    {p.name}
                    {p.study_type && (
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                        background: `${color}18`, color,
                      }}>
                        {p.study_type}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                className="btn btn-primary"
                onClick={handleCompare}
                disabled={loading || selected.size < 2}
              >
                {loading ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Loading…</> : "Compare"}
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => { setSelected(new Set()); setComparison([]); }}>
                Clear
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => { setSelected(new Set(allProjects.map(p => p.id))); setComparison([]); }}>
                Select All
              </button>
            </div>
          </div>

          {/* Comparison matrix */}
          {comparison.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 600 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--border)" }}>
                    <th style={{
                      textAlign: "left", padding: "10px 14px",
                      fontSize: 11, color: "var(--text-tertiary)",
                      fontWeight: 600, textTransform: "uppercase",
                      letterSpacing: "0.06em", width: 180, position: "sticky", left: 0,
                      background: "var(--surface)",
                    }}>
                      Metric
                    </th>
                    {comparison.map(p => (
                      <th key={p.project_id} style={{
                        textAlign: "left", padding: "10px 14px",
                        fontWeight: 700, fontSize: 13,
                        color: "var(--text-primary)",
                        minWidth: 160,
                      }}>
                        <Link
                          to={`/projects/${p.project_id}`}
                          style={{ color: "inherit", textDecoration: "none" }}
                        >
                          {p.name}
                        </Link>
                        <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                          {p.commodity && (
                            <span style={{ fontSize: 10, color: "var(--text-tertiary)", fontWeight: 400 }}>{p.commodity}</span>
                          )}
                          {!p.has_report && (
                            <span style={{
                              fontSize: 10, padding: "1px 5px", borderRadius: 3,
                              background: "rgba(107,114,128,0.1)", color: "var(--text-tertiary)",
                              fontWeight: 600,
                            }}>No report</span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRIC_GROUPS.map(({ group, metrics }) => (
                    <>
                      {/* Group header */}
                      <tr key={`group-${group}`} style={{ background: "var(--surface-alt, rgba(0,0,0,0.02))" }}>
                        <td colSpan={comparison.length + 1} style={{
                          padding: "8px 14px",
                          fontSize: 10, fontWeight: 700,
                          textTransform: "uppercase", letterSpacing: "0.08em",
                          color: "var(--text-tertiary)",
                          borderTop: "1px solid var(--border)",
                        }}>
                          {group}
                        </td>
                      </tr>
                      {metrics.map(({ label, key, format, higherIsBetter }) => {
                        const highlights = higherIsBetter !== undefined
                          ? getHighlights(comparison, key, higherIsBetter)
                          : new Map();
                        return (
                          <tr key={key} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                            <td style={{
                              padding: "9px 14px",
                              color: "var(--text-secondary)",
                              fontWeight: 500,
                              fontSize: 12,
                              position: "sticky",
                              left: 0,
                              background: "var(--surface)",
                            }}>
                              {label}
                            </td>
                            {comparison.map(p => {
                              const highlight = highlights.get(p.project_id);
                              return (
                                <td key={p.project_id} style={{
                                  padding: "9px 14px",
                                  fontWeight: highlight ? 700 : 400,
                                  color: highlight === "best" ? "#16a34a"
                                    : highlight === "worst" ? "#dc3535"
                                    : "var(--text-primary)",
                                  background: highlight === "best" ? "rgba(34,197,94,0.05)"
                                    : highlight === "worst" ? "rgba(220,53,53,0.05)"
                                    : "transparent",
                                }}>
                                  {format(p[key], p)}
                                  {highlight === "best" && (
                                    <span style={{ marginLeft: 5, fontSize: 10, opacity: 0.7 }}>▲ best</span>
                                  )}
                                  {highlight === "worst" && (
                                    <span style={{ marginLeft: 5, fontSize: 10, opacity: 0.7 }}>▼ worst</span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </>
                  ))}
                </tbody>
              </table>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10, padding: "0 4px" }}>
                Green = best value in group · Red = worst value · Economics pulled from most recent completed run · Resource data from manually entered resource table
              </div>
            </div>
          )}

          {comparison.length === 0 && !loading && (
            <div className="empty-state" style={{ marginTop: 0 }}>
              <h3>Select projects and click Compare</h3>
              <p>The matrix will show all metrics side by side with best/worst highlighted</p>
            </div>
          )}
        </>
      )}
    </>
  );
}
