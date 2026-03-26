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
// Grade–Tonnage Bubble Chart
// ---------------------------------------------------------------------------

function GradeTonnageChart({ projects }: { projects: ProjectMetrics[] }) {
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; name: string; tonnage: number; grade: number;
    npv: number | null; stage: string;
  } | null>(null);

  const plotData = projects.filter(
    (p) => p.total_resource_mt != null && (p.total_resource_mt as number) > 0
      && p.primary_grade != null && (p.primary_grade as number) > 0
  );

  if (plotData.length < 2) return null;

  const W = 600, H = 340;
  const ML = 60, MR = 24, MT = 20, MB = 48;
  const iW = W - ML - MR;
  const iH = H - MT - MB;

  const tons   = plotData.map(p => p.total_resource_mt as number);
  const grades = plotData.map(p => p.primary_grade as number);
  const npvs   = plotData.map(p => p.npv_musd).filter((v): v is number => v != null);

  // Padded log-scale extents
  const tMin = Math.min(...tons)   / 2, tMax = Math.max(...tons)   * 2;
  const gMin = Math.min(...grades) / 2, gMax = Math.max(...grades) * 2;
  const npvMin = npvs.length ? Math.min(...npvs) : 0;
  const npvMax = npvs.length ? Math.max(...npvs) : 1;

  const lx = (v: number) => (Math.log(v / tMin) / Math.log(tMax / tMin)) * iW;
  const ly = (v: number) => iH - (Math.log(v / gMin) / Math.log(gMax / gMin)) * iH;
  const lr = (v: number | null) =>
    v == null || npvMax <= npvMin ? 16 : 12 + ((v - npvMin) / (npvMax - npvMin)) * 28;

  // Minimal log tick generator
  function logTicks(min: number, max: number): number[] {
    const result: number[] = [];
    let mag = Math.floor(Math.log10(min));
    let base = Math.pow(10, mag);
    while (base <= max * 1.5) {
      for (const m of [1, 2, 5]) {
        const t = base * m;
        if (t >= min * 0.8 && t <= max * 1.5) result.push(t);
      }
      base *= 10;
    }
    return [...new Set(result)].sort((a, b) => a - b);
  }

  const xTicks = logTicks(tMin, tMax);
  const yTicks = logTicks(gMin, gMax);

  const stageColor: Record<string, string> = {
    PEA: "#f59e0b", PFS: "#0891b2", FS: "#16a34a", scoping: "#d97706", other: "#6b7280",
  };
  const presentStages = [...new Set(plotData.map(p => p.study_type ?? "other"))];

  const fmtTon = (v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`;

  return (
    <div style={{ marginTop: 48 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, letterSpacing: "0.07em",
        textTransform: "uppercase", color: "var(--text-tertiary)", marginBottom: 6,
      }}>
        Grade–Tonnage Comparison
      </div>
      <p style={{ fontSize: 13, color: "var(--text-tertiary)", margin: "0 0 16px" }}>
        Bubble size = NPV &nbsp;·&nbsp; Colour = study stage &nbsp;·&nbsp; Log scale both axes
      </p>

      <div style={{ position: "relative", display: "inline-block" }}>
        <svg width={W} height={H} style={{ overflow: "visible", display: "block" }}>
          <g transform={`translate(${ML},${MT})`}>
            {/* Grid lines */}
            {xTicks.map(t => (
              <line key={`gx${t}`} x1={lx(t)} x2={lx(t)} y1={0} y2={iH}
                stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3,3" />
            ))}
            {yTicks.map(t => (
              <line key={`gy${t}`} x1={0} x2={iW} y1={ly(t)} y2={ly(t)}
                stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3,3" />
            ))}

            {/* X axis */}
            {xTicks.map(t => (
              <g key={`xt${t}`} transform={`translate(${lx(t)},${iH})`}>
                <line y2={5} stroke="var(--border)" />
                <text y={18} textAnchor="middle" fontSize={10} fill="var(--text-tertiary)">
                  {fmtTon(t)}
                </text>
              </g>
            ))}
            <text x={iW / 2} y={iH + 40} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">
              Total Resource (Mt)
            </text>

            {/* Y axis */}
            {yTicks.map(t => (
              <g key={`yt${t}`} transform={`translate(0,${ly(t)})`}>
                <line x2={-5} stroke="var(--border)" />
                <text x={-8} textAnchor="end" dominantBaseline="middle" fontSize={10} fill="var(--text-tertiary)">
                  {t}
                </text>
              </g>
            ))}
            <text
              transform={`translate(-48,${iH / 2}) rotate(-90)`}
              textAnchor="middle" fontSize={11} fill="var(--text-secondary)"
            >
              Primary Grade (g/t)
            </text>

            {/* Bubbles */}
            {plotData.map(p => {
              const cx = lx(p.total_resource_mt as number);
              const cy = ly(p.primary_grade as number);
              const r  = lr(p.npv_musd ?? null);
              const color = stageColor[p.study_type ?? "other"] ?? "#6b7280";
              return (
                <g key={p.project_id}>
                  <circle
                    cx={cx} cy={cy} r={r}
                    fill={color} fillOpacity={0.72}
                    stroke={color} strokeWidth={1.5}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={(e) => setTooltip({
                      x: e.clientX, y: e.clientY,
                      name: p.name,
                      tonnage: p.total_resource_mt as number,
                      grade: p.primary_grade as number,
                      npv: p.npv_musd ?? null,
                      stage: p.study_type ?? "—",
                    })}
                    onMouseLeave={() => setTooltip(null)}
                  />
                </g>
              );
            })}

            {/* Chart border */}
            <rect x={0} y={0} width={iW} height={iH}
              fill="none" stroke="var(--border)" strokeWidth={1} />
          </g>
        </svg>

        {/* Stage legend */}
        <div style={{ display: "flex", gap: 14, marginTop: 10, flexWrap: "wrap" }}>
          {presentStages.map(stage => (
            <span key={stage} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--text-secondary)" }}>
              <span style={{
                width: 10, height: 10, borderRadius: "50%",
                background: stageColor[stage] ?? "#6b7280", display: "inline-block",
              }} />
              {stage}
            </span>
          ))}
        </div>
      </div>

      {/* Fixed tooltip */}
      {tooltip && (
        <div style={{
          position: "fixed",
          left: tooltip.x + 14,
          top: tooltip.y - 80,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "10px 14px",
          fontSize: 13,
          boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
          pointerEvents: "none",
          zIndex: 9999,
          minWidth: 160,
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--text-primary)" }}>{tooltip.name}</div>
          <div style={{ color: "var(--text-secondary)" }}>
            {tooltip.tonnage.toLocaleString()} Mt &nbsp;·&nbsp; {tooltip.grade} g/t
          </div>
          {tooltip.npv != null && (
            <div style={{ color: "var(--text-secondary)" }}>NPV: ${tooltip.npv.toLocaleString()}M</div>
          )}
          <div style={{ color: "var(--text-tertiary)", fontSize: 11, marginTop: 3 }}>{tooltip.stage}</div>
        </div>
      )}
    </div>
  );
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
          <h3>Portfolio comparison needs at least 2 projects</h3>
          <p>
            Run analysis on at least 2 projects to compare them. Portfolio comparison pulls
            grade, tonnage, NPV, and IRR automatically from each completed run.
          </p>
          <Link to="/projects" className="btn btn-primary" style={{ marginTop: 16 }}>
            Go to Projects
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

          {/* Comparison matrix + bubble chart */}
          {comparison.length > 0 && (
            <>
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

            <GradeTonnageChart projects={comparison} />
            </>
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
