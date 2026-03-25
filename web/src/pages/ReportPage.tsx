import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport } from "../api/client";

// Same base URL logic as client.ts — no Vite proxy in the Tauri bundle
const API_BASE = import.meta.env.PROD ? "http://127.0.0.1:8000" : "/api";
import { useToast } from "../components/shared/Toast";
import type { ReportContent } from "../types";

// ── Download ────────────────────────────────────────────────────────────────

async function downloadReport(
  projectId: string,
  runId: string,
  format: "json" | "md" | "txt" | "pdf"
) {
  const url = `${API_BASE}/projects/${projectId}/reports/${runId}/export?format=${format}`;
  const res = await fetch(url);
  if (!res.ok) {
    alert("Export failed — check that the server is running.");
    return;
  }
  const blob = await res.blob();
  const filename = `${projectId}_${runId}_report.${format}`;

  if (typeof window !== "undefined" && (window as any).__TAURI__) {
    const { save } = await import("@tauri-apps/api/dialog");
    const { writeBinaryFile } = await import("@tauri-apps/api/fs");
    const buffer = await blob.arrayBuffer();
    const filePath = await save({
      defaultPath: filename,
      filters: [{ name: format.toUpperCase(), extensions: [format] }],
    });
    if (filePath) await writeBinaryFile(filePath, new Uint8Array(buffer));
    return;
  }

  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(blobUrl);
}

// ── Icons ───────────────────────────────────────────────────────────────────

function DownloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

// ── Layer 1: Narrative components ────────────────────────────────────────────

function KeyCallouts({ callouts }: { callouts: { label: string; value: string; context?: string }[] }) {
  if (!callouts?.length) return null;
  return (
    <div className="report-callouts-grid">
      {callouts.map((c, i) => (
        <div key={i} className="report-callout-card">
          <div className="report-callout-value">{c.value}</div>
          <div className="report-callout-label">{c.label}</div>
          {c.context && <div className="report-callout-context">{c.context}</div>}
        </div>
      ))}
    </div>
  );
}

function NarrativeSection({ assembly }: { assembly: Record<string, unknown> }) {
  const narrative = assembly.narrative as string | undefined;
  const conclusion = assembly.analyst_conclusion as string | undefined;
  const callouts = assembly.key_callouts as { label: string; value: string; context?: string }[] | undefined;
  const flags = assembly.consistency_flags as string[] | undefined;
  const disclaimer = assembly.disclaimer as string | undefined;

  const paragraphs = narrative
    ? narrative.split(/\n\n+/).map((p) => p.trim()).filter(Boolean)
    : [];

  return (
    <div className="report-narrative-section">
      <KeyCallouts callouts={callouts ?? []} />

      {paragraphs.length > 0 && (
        <div className="report-narrative-body">
          {paragraphs.map((para, i) => (
            <p key={i} className="report-narrative-para">{para}</p>
          ))}
        </div>
      )}

      {conclusion && (
        <div className="report-narrative-conclusion">
          <p>{conclusion}</p>
        </div>
      )}

      {flags && flags.length > 0 && (
        <div className="report-consistency-flags">
          <div className="report-flags-label">Consistency notes</div>
          {flags.map((f, i) => (
            <div key={i} className="report-flag-item">⚠ {f}</div>
          ))}
        </div>
      )}

      {disclaimer && (
        <div className="report-disclaimer-block">{disclaimer}</div>
      )}
    </div>
  );
}

// ── Layer 2: Specialist section renderers ────────────────────────────────────

function DataTable({ items }: { items: Record<string, unknown>[] }) {
  if (!items.length) return null;
  const cols = Object.keys(items[0]);
  return (
    <div style={{ overflowX: "auto", marginTop: 16 }}>
      <table className="report-table">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c}>{c.replace(/_/g, " ")}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{row[c] === null || row[c] === undefined ? "—" : String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProseField({ label, value, showLabel }: { label: string; value: string; showLabel: boolean }) {
  return (
    <div className="report-prose-para">
      {showLabel && (
        <div className="report-para-label">{label.replace(/_/g, " ")}</div>
      )}
      <p>{value}</p>
    </div>
  );
}

function SpecialistSection({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  const prose = entries.filter(([, v]) => typeof v === "string" && (v as string).length > 60);
  const lists = entries.filter(([, v]) => Array.isArray(v) && (v as unknown[]).length > 0);
  const scalars = entries.filter(
    ([k]) => !prose.find(([pk]) => pk === k) && !lists.find(([lk]) => lk === k)
  );
  const isSingleProse = prose.length === 1 && lists.length === 0 && scalars.length === 0;

  return (
    <div className="report-specialist-body">
      {prose.map(([k, v]) => (
        <ProseField key={k} label={k} value={String(v)} showLabel={!isSingleProse} />
      ))}

      {lists.map(([k, v]) => {
        const items = v as unknown[];
        if (!items.length) return null;
        const isObjectArray = typeof items[0] === "object" && items[0] !== null;
        return (
          <div key={k} style={{ marginTop: 20 }}>
            <div className="report-sub-label">
              {k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </div>
            {isObjectArray ? (
              <DataTable items={items as Record<string, unknown>[]} />
            ) : (
              <ul className="report-bullet-list">
                {items.map((item, i) => (
                  <li key={i}>
                    <span className="report-bullet">—</span>
                    <span>{String(item)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}

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

function DcfSection({ data }: { data: Record<string, unknown> }) {
  const [showCashFlow, setShowCashFlow] = useState(false);

  if (!data.model_ran) {
    return (
      <div className="report-specialist-body">
        <p style={{ color: "var(--r-ink-3)", fontStyle: "italic" }}>
          {String(data.reason ?? "DCF model did not run.")}
        </p>
      </div>
    );
  }

  const summary = data.summary as Record<string, unknown> | undefined;
  const cashFlows = data.cash_flow_table as Record<string, unknown>[] | undefined;
  const sensitivity = data.sensitivity as Record<string, unknown> | undefined;
  const notes = data.assumptions_notes as string | undefined;

  return (
    <div className="report-specialist-body">
      {notes && (
        <div className="report-dcf-notes">
          <strong>Model assumptions:</strong> {notes}
        </div>
      )}

      {summary && (
        <>
          <div className="report-sub-label">Valuation Summary</div>
          <div className="report-scalar-row" style={{ marginTop: 8 }}>
            {Object.entries(summary)
              .filter(([k, v]) => v !== null && !["project_id", "scenario", "after_tax", "notes", "aisc_unit"].includes(k))
              .map(([k, v]) => (
                <div key={k} className="report-scalar-chip">
                  <span className="report-scalar-label">{k.replace(/_/g, " ")}</span>
                  <span className="report-scalar-value">
                    {typeof v === "number" ? v.toLocaleString() : String(v)}
                    {k.includes("musd") ? " M USD" : ""}
                    {k.includes("percent") ? "%" : ""}
                    {k.includes("years") && !k.includes("depreciation") ? " yrs" : ""}
                  </span>
                </div>
              ))}
          </div>
        </>
      )}

      {sensitivity && (
        <>
          <div className="report-sub-label" style={{ marginTop: 24 }}>Sensitivity Analysis</div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            Base NPV: {(sensitivity as any).base_npv_musd} M USD
            {(sensitivity as any).base_irr_percent != null &&
              ` · Base IRR: ${(sensitivity as any).base_irr_percent}%`}
          </p>
        </>
      )}

      {cashFlows && cashFlows.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <button
            className="btn btn-secondary btn-sm"
            style={{ marginBottom: 12 }}
            onClick={() => setShowCashFlow((v) => !v)}
          >
            {showCashFlow ? "Hide" : "Show"} cash flow table ({cashFlows.length} periods)
          </button>
          {showCashFlow && <DataTable items={cashFlows} />}
        </div>
      )}
    </div>
  );
}

// ── Data Gap Section ─────────────────────────────────────────────────────────

type DataGap = {
  domain: string;
  gap_description: string;
  impact_on_analysis: string;
  blocking_advancement: boolean;
  recommended_action: string;
  urgency: "critical" | "important" | "minor";
};

function DataGapSection({ data }: { data: Record<string, unknown> }) {
  const gaps = (data.data_gaps as DataGap[]) ?? [];
  const overall = data.overall_data_quality_comment as string | undefined;
  const critical = data.critical_gaps_count as number | undefined;
  const important = data.important_gaps_count as number | undefined;
  const minor = data.minor_gaps_count as number | undefined;

  const urgencyStyle: Record<string, React.CSSProperties> = {
    critical: { color: "var(--danger)", fontWeight: 600 },
    important: { color: "var(--warning)", fontWeight: 600 },
    minor:    { color: "var(--text-tertiary)", fontWeight: 500 },
  };

  return (
    <div className="report-specialist-body">
      {overall && (
        <p style={{ marginBottom: 20, lineHeight: 1.7 }}>{overall}</p>
      )}

      {/* Summary counts */}
      {(critical != null || important != null || minor != null) && (
        <div style={{ display: "flex", gap: 20, marginBottom: 24, paddingBottom: 16, borderBottom: "1px solid var(--border)" }}>
          {critical != null && (
            <div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--danger)" }}>{critical}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Critical</div>
            </div>
          )}
          {important != null && (
            <div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--warning)" }}>{important}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Important</div>
            </div>
          )}
          {minor != null && (
            <div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-secondary)" }}>{minor}</div>
              <div style={{ fontSize: 12, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Minor</div>
            </div>
          )}
        </div>
      )}

      {/* Gap list */}
      {gaps.map((gap, i) => (
        <div key={i} style={{
          paddingBottom: 20,
          marginBottom: 20,
          borderBottom: i < gaps.length - 1 ? "1px solid var(--border)" : "none",
        }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>{gap.domain}</span>
            <span style={{ fontSize: 12, ...urgencyStyle[gap.urgency] }}>
              {gap.urgency?.toUpperCase()}
            </span>
            {gap.blocking_advancement && (
              <span style={{ fontSize: 11, color: "var(--danger)", background: "var(--danger-light)", padding: "1px 7px", borderRadius: 4 }}>
                blocks advancement
              </span>
            )}
          </div>
          {gap.gap_description && gap.gap_description !== "No material gaps identified" && (
            <p style={{ margin: "0 0 6px", fontSize: 14, lineHeight: 1.6 }}>{gap.gap_description}</p>
          )}
          {gap.impact_on_analysis && (
            <p style={{ margin: "0 0 4px", fontSize: 13, color: "var(--text-secondary)", fontStyle: "italic" }}>
              Impact: {gap.impact_on_analysis}
            </p>
          )}
          {gap.recommended_action && (
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              Action: {gap.recommended_action}
            </p>
          )}
        </div>
      ))}

      {gaps.length === 0 && (
        <p style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>No data gaps identified.</p>
      )}
    </div>
  );
}

function ImageGallery({
  projectId,
  imageFiles,
  renderFiles,
}: {
  projectId: string;
  imageFiles: string[];
  renderFiles: string[];
}) {
  const all = [...new Set([...imageFiles, ...renderFiles])];
  if (!all.length) return null;

  return (
    <div className="report-image-gallery">
      <div className="report-sub-label">Visual References</div>
      {all.map((name) => (
        <figure key={name} className="report-image-figure">
          <img
            src={`${API_BASE}/projects/${projectId}/files/${encodeURIComponent(name)}/content`}
            alt={name}
            className="report-image"
            loading="lazy"
          />
          <figcaption className="report-image-caption">{name}</figcaption>
        </figure>
      ))}
    </div>
  );
}

function DataSourcesSection({
  projectId,
  data,
}: {
  projectId: string;
  data: Record<string, unknown>;
}) {
  const files = (data.source_files as string[]) ?? [];
  const imageFiles = (data.image_files as string[]) ?? [];
  const renderFiles = (data.render_files as string[]) ?? [];

  return (
    <div className="report-specialist-body">
      <div className="report-notice">{String(data.notice ?? "")}</div>
      {files.length > 0 && (
        <>
          <div className="report-sub-label">
            Source Documents ({files.length})
          </div>
          <div className="report-file-list">
            {files.map((f, i) => (
              <div key={i} className="report-file-row">
                <div className="report-file-check">✓</div>
                {f}
              </div>
            ))}
          </div>
        </>
      )}
      <ImageGallery projectId={projectId} imageFiles={imageFiles} renderFiles={renderFiles} />
      {data.generated_at != null && (
        <div style={{ fontSize: 12, color: "var(--r-ink-4)", marginTop: 20 }}>
          Generated: {new Date(String(data.generated_at)).toLocaleString()}
        </div>
      )}
    </div>
  );
}

// ── Section layout config ────────────────────────────────────────────────────

type SectionLayer = "narrative" | "detail" | "appendix" | "hidden";

const SECTION_CONFIG: Record<string, {
  title: string;
  subtitle?: string;
  layer: SectionLayer;
  number?: string;
}> = {
  "07_assembly":        { title: "Analyst Narrative", layer: "narrative" },
  "03_geology":         { title: "Geology & Resources", subtitle: "Deposit geology and resource assessment", layer: "detail", number: "1" },
  "04_economics":       { title: "Economics & Financial Analysis", subtitle: "Capital costs, operating costs, and financial projections", layer: "detail", number: "2" },
  "05_risks":           { title: "Risks & Uncertainties", subtitle: "Material risks and mitigations", layer: "detail", number: "3" },
  "06_dcf_model":       { title: "DCF Financial Model", subtitle: "Computed discounted cash flow analysis", layer: "detail", number: "4" },
  "08_data_gaps":       { title: "Data Gap Report", subtitle: "Material information gaps and recommended actions", layer: "detail", number: "5" },
  "00_data_sources":    { title: "Appendix A — Source Documents", subtitle: "All documents used in this analysis", layer: "appendix" },
  "01_project_facts":   { title: "Project Facts", layer: "hidden" },
  "02_executive_summary": { title: "Executive Summary", layer: "hidden" }, // legacy — replaced by assembly
};

// ── Table of contents ────────────────────────────────────────────────────────

function TableOfContents({
  sections,
  activeSection,
  onNav,
}: {
  sections: { key: string; title: string; number?: string }[];
  activeSection: string | null;
  onNav: (key: string) => void;
}) {
  return (
    <nav className="report-toc">
      <div className="report-toc-label">Contents</div>
      {sections.map((s) => (
        <button
          key={s.key}
          className={`report-toc-item${activeSection === s.key ? " active" : ""}`}
          onClick={() => onNav(s.key)}
        >
          {s.number && <span className="report-toc-num">{s.number}</span>}
          <span>{s.title}</span>
        </button>
      ))}
    </nav>
  );
}

// ── Report Page ──────────────────────────────────────────────────────────────

export default function ReportPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const { toast } = useToast();
  const [report, setReport] = useState<ReportContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const id = projectId!;
  const rid = runId!;

  useEffect(() => {
    getReport(id, rid)
      .then(setReport)
      .catch((err) => toast(err.message ?? "Could not load report", "error"))
      .finally(() => setLoading(false));
  }, [id, rid]);

  // Intersection observer for active TOC item
  useEffect(() => {
    if (!report) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length > 0) setActiveSection(visible[0].target.id);
      },
      { threshold: 0.2 }
    );
    Object.values(sectionRefs.current).forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, [report]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <span className="spinner" style={{ width: 28, height: 28, color: "var(--text-tertiary)" }} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="empty-state">
        <h3>Report not found</h3>
        <p>This run may still be in progress or may have failed.</p>
        <Link to={`/projects/${id}`} className="btn btn-secondary" style={{ marginTop: 8 }}>
          Back to Project
        </Link>
      </div>
    );
  }

  const sections = report.sections;
  const projectName = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const generatedAt = new Date().toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });

  // Order and categorise sections
  const orderedKeys = Object.keys(sections).sort();
  const narrativeKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "narrative");
  const detailKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "detail");
  const appendixKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "appendix");

  const tocSections = [
    ...narrativeKeys.map((k) => ({ key: k, title: "Analyst Narrative" })),
    ...detailKeys.map((k) => ({
      key: k,
      title: SECTION_CONFIG[k]?.title ?? k,
      number: SECTION_CONFIG[k]?.number,
    })),
    ...appendixKeys.map((k) => ({
      key: k,
      title: SECTION_CONFIG[k]?.title ?? k,
    })),
  ];

  const scrollTo = (key: string) => {
    sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const renderSection = (key: string) => {
    const content = sections[key];
    if (key === "00_data_sources") {
      return <DataSourcesSection projectId={id} data={content as Record<string, unknown>} />;
    }
    if (key === "06_dcf_model") {
      return <DcfSection data={content as Record<string, unknown>} />;
    }
    if (key === "07_assembly") {
      return <NarrativeSection assembly={content as Record<string, unknown>} />;
    }
    if (key === "08_data_gaps") {
      return <DataGapSection data={content as Record<string, unknown>} />;
    }
    if (typeof content === "object" && content !== null && !Array.isArray(content)) {
      return <SpecialistSection data={content as Record<string, unknown>} />;
    }
    return <pre style={{ fontSize: 12, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
  };

  return (
    <div className="report-page-layout">
      {/* Left TOC */}
      <aside className="report-toc-aside">
        <TableOfContents
          sections={tocSections}
          activeSection={activeSection}
          onNav={scrollTo}
        />
      </aside>

      {/* Main content */}
      <main className="report-main">
        {/* Cover */}
        <div className="report-cover">
          <div className="report-cover-eyebrow">Extract — Technical Analysis Report</div>
          <div className="report-cover-title">{projectName}</div>
          <div className="report-cover-subtitle">
            {(sections["07_assembly"] as any)?.study_level &&
              (sections["07_assembly"] as any)?.study_level !== "unknown"
              ? `${(sections["07_assembly"] as any).study_level} · `
              : ""}
            {(sections["07_assembly"] as any)?.project_stage ?? "Technical Analysis"}
          </div>

          <div className="report-cover-meta">
            {[
              ["Report Date", generatedAt],
              ["Run ID", rid],
              ["Classification", "Internal — Confidential"],
              ["Prepared By", "Extract AI"],
            ].map(([label, value]) => (
              <div key={label} className="report-cover-meta-item">
                <div className="report-cover-meta-label">{label}</div>
                <div className="report-cover-meta-value">{value}</div>
              </div>
            ))}
          </div>

          <div className="report-disclaimer">
            This report is generated by an AI system for internal research purposes only. It does
            not constitute investment advice or a formal technical study. All data should be verified
            against primary source documents.
          </div>

          <div className="report-export-row">
            <span style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>
              {detailKeys.length} sections · {(sections["00_data_sources"] as any)?.file_count ?? 0} source documents
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-primary btn-sm" onClick={() => downloadReport(id, rid, "pdf")}>
                <DownloadIcon /> PDF
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "md")}>
                <DownloadIcon /> Markdown
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "json")}>
                <DownloadIcon /> JSON
              </button>
            </div>
          </div>
        </div>

        {/* Layer 1 — Analyst Narrative */}
        {narrativeKeys.map((key) => (
          <div
            key={key}
            id={key}
            ref={(el) => { sectionRefs.current[key] = el; }}
            className="report-narrative-wrapper"
          >
            {renderSection(key)}
          </div>
        ))}

        {/* Layer 2 — Detailed sections */}
        {detailKeys.length > 0 && (
          <div className="report-detail-label">Detailed Analysis</div>
        )}
        {detailKeys.map((key) => {
          const cfg = SECTION_CONFIG[key];
          return (
            <div
              key={key}
              id={key}
              ref={(el) => { sectionRefs.current[key] = el; }}
              className="report-section"
            >
              <div className="report-section-header">
                <div className="report-section-heading">
                  {cfg?.number && (
                    <div className="report-section-number">Section {cfg.number}</div>
                  )}
                  <div className="report-section-title">{cfg?.title ?? key}</div>
                  {cfg?.subtitle && (
                    <div className="report-section-subtitle">{cfg.subtitle}</div>
                  )}
                </div>
              </div>
              {renderSection(key)}
            </div>
          );
        })}

        {/* Appendix */}
        {appendixKeys.length > 0 && (
          <div className="report-detail-label">Appendix</div>
        )}
        {appendixKeys.map((key) => {
          const cfg = SECTION_CONFIG[key];
          return (
            <div
              key={key}
              id={key}
              ref={(el) => { sectionRefs.current[key] = el; }}
              className="report-section report-section--appendix"
            >
              <div className="report-section-header">
                <div className="report-section-heading">
                  <div className="report-section-title">{cfg?.title ?? key}</div>
                  {cfg?.subtitle && (
                    <div className="report-section-subtitle">{cfg.subtitle}</div>
                  )}
                </div>
              </div>
              {renderSection(key)}
            </div>
          );
        })}
      </main>
    </div>
  );
}
