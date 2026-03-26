import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getReport } from "../api/client";

// Same base URL logic as client.ts — no Vite proxy in the Tauri bundle
const API_BASE = import.meta.env.PROD ? "http://127.0.0.1:8000" : "/api";
import { useToast } from "../components/shared/Toast";
import type { ReportContent } from "../types";

// ── Download ────────────────────────────────────────────────────────────────

async function downloadReport(
  projectId: string,
  runId: string,
  format: "json" | "md" | "txt" | "pdf" | "pptx"
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

function NarrativeSection({ assembly, projectId }: {
  assembly: Record<string, unknown>;
  projectId?: string;
}) {
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
          {paragraphs.map((para, i) => {
            if (para.includes("{{FIGURE:") && projectId) {
              return <React.Fragment key={i}>{renderProseWithFigures(para, projectId)}</React.Fragment>;
            }
            return <p key={i} className="report-narrative-para">{para}</p>;
          })}
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

// ── Figure placeholder substitution ──────────────────────────────────────────
// Handles {{FIGURE: filename | Caption text}} injected by the LLM into prose.

// Non-global: safe to reuse for both detection (.includes fast path) and extraction.
const FIGURE_RE = /\{\{FIGURE:\s*([^|]+)\|([^}]+)\}\}/;

function renderProseWithFigures(text: string, projectId: string): React.ReactNode[] {
  const parts = text.split(/(\{\{FIGURE:\s*[^|]+\|[^}]+\}\})/);
  return parts.map((part, i) => {
    const match = part.match(FIGURE_RE);
    if (match) {
      const filename = match[1].trim();
      const caption  = match[2].trim();
      return (
        <figure key={i} style={{ margin: "32px 0", textAlign: "center" }}>
          <img
            src={`${API_BASE}/projects/${projectId}/renders/${filename}`}
            alt={caption}
            style={{ maxWidth: "100%", borderRadius: 8, border: "1px solid var(--border)" }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
          <figcaption style={{
            fontSize: 12,
            color: "var(--text-tertiary)",
            marginTop: 8,
            fontStyle: "italic",
            lineHeight: 1.5,
          }}>
            {caption}
          </figcaption>
        </figure>
      );
    }
    if (!part.trim()) return null;
    return <p key={i} className="report-prose-para">{part}</p>;
  }).filter(Boolean) as React.ReactNode[];
}

function ProseField({ label, value, showLabel, projectId }: {
  label: string;
  value: string;
  showLabel: boolean;
  projectId?: string;
}) {
  return (
    <div className="report-prose-para">
      {showLabel && (
        <div className="report-para-label">{label.replace(/_/g, " ")}</div>
      )}
      {value.includes("{{FIGURE:") && projectId
        ? renderProseWithFigures(value, projectId)
        : <p>{value}</p>
      }
    </div>
  );
}

function SpecialistSection({ data, projectId }: { data: Record<string, unknown>; projectId?: string }) {
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
        <ProseField key={k} label={k} value={String(v)} showLabel={!isSingleProse} projectId={projectId} />
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

      {summary && (() => {
        const rows = Object.entries(summary).filter(([k, v]) =>
          v !== null && !["project_id", "scenario", "after_tax", "notes", "aisc_unit"].includes(k)
        );
        if (!rows.length) return null;
        const fmt = (k: string, v: unknown) => {
          const s = typeof v === "number" ? v.toLocaleString() : String(v);
          if (k.includes("musd")) return s + " M USD";
          if (k.includes("percent")) return s + "%";
          if (k.includes("years") && !k.includes("depreciation")) return s + " yrs";
          return s;
        };
        const label = (k: string) =>
          k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        return (
          <>
            <div className="report-sub-label">Valuation Summary</div>
            <div style={{ overflowX: "auto", marginTop: 8 }}>
              <table className="report-table report-param-table">
                <tbody>
                  {rows.map(([k, v]) => (
                    <tr key={k}>
                      <td className="report-param-key">{label(k)}</td>
                      <td className="report-param-val">{fmt(k, v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        );
      })()}

      {sensitivity && (() => {
        const s = sensitivity as Record<string, unknown>;
        const baseNpv = s.base_npv_musd;
        const baseIrr = s.base_irr_percent;
        const scenarios = Object.entries(s).filter(([k]) =>
          !["base_npv_musd", "base_irr_percent"].includes(k) && typeof s[k] === "object"
        );
        return (
          <>
            <div className="report-sub-label" style={{ marginTop: 32 }}>Sensitivity Analysis</div>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "8px 0 16px", lineHeight: 1.7 }}>
              Base case: NPV {baseNpv != null ? `${baseNpv} M USD` : "n/a"}
              {baseIrr != null ? ` · IRR ${baseIrr}%` : ""}
            </p>
            {scenarios.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table className="report-table">
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      {Object.keys((scenarios[0][1] as Record<string, unknown>) ?? {}).map(k => (
                        <th key={k}>{k.replace(/_/g, " ")}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {scenarios.map(([k, v]) => {
                      const row = v as Record<string, unknown>;
                      return (
                        <tr key={k}>
                          <td style={{ fontWeight: 500 }}>{k.replace(/_/g, " ")}</td>
                          {Object.values(row).map((val, i) => (
                            <td key={i}>{val != null ? String(val) : "—"}</td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        );
      })()}

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

  const priorityLabel: Record<string, string> = {
    critical: "Critical",
    important: "Important",
    minor: "Minor",
  };

  const visibleGaps = gaps.filter(
    (g) => !g.gap_description || g.gap_description !== "No material gaps identified"
  );

  return (
    <div className="report-specialist-body">
      {overall && <p style={{ marginBottom: 24, lineHeight: 1.85 }}>{overall}</p>}

      {visibleGaps.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table className="report-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Gap</th>
                <th>Impact on Analysis</th>
                <th>Recommended Action</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {visibleGaps.map((gap, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500, whiteSpace: "nowrap" }}>
                    {gap.domain}
                    {gap.blocking_advancement && (
                      <span title="Blocks study advancement" style={{ marginLeft: 4, color: "var(--text-tertiary)", fontSize: 11 }}>†</span>
                    )}
                  </td>
                  <td style={{ lineHeight: 1.6 }}>{gap.gap_description}</td>
                  <td style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{gap.impact_on_analysis ?? "—"}</td>
                  <td style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{gap.recommended_action ?? "—"}</td>
                  <td style={{ whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                    {priorityLabel[gap.urgency] ?? gap.urgency}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {visibleGaps.some((g) => g.blocking_advancement) && (
            <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 8, fontStyle: "italic" }}>
              † Item blocks study advancement to next stage.
            </p>
          )}
        </div>
      ) : (
        <p style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>No material data gaps identified.</p>
      )}
    </div>
  );
}

// ── Confidence Assessment Section ────────────────────────────────────────────

type DomainConfidence = {
  domain: string;
  confidence_descriptor: string;
  supporting_factors: string[];
  limiting_factors: string[];
};

function ConfidenceSection({ data }: { data: Record<string, unknown> }) {
  const overall = data.overall_confidence_statement as string | undefined;
  const best    = data.most_reliable_aspect as string | undefined;
  const worst   = data.least_reliable_aspect as string | undefined;
  const domains = (data.domain_confidence as DomainConfidence[]) ?? [];

  return (
    <div className="report-specialist-body">
      {overall && <p style={{ lineHeight: 1.85, marginBottom: 20 }}>{overall}</p>}

      {(best || worst) && (
        <p style={{ lineHeight: 1.85, marginBottom: 24, color: "var(--text-secondary)", fontSize: 14 }}>
          {best && <>The most reliably supported aspect of this analysis is {best.toLowerCase().endsWith(".") ? best : best + "."}</>}
          {best && worst && " "}
          {worst && <>The least reliable aspect, where additional verification is recommended, is {worst.toLowerCase().endsWith(".") ? worst : worst + "."}</>}
        </p>
      )}

      {domains.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="report-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>Assessment</th>
                <th>Supports Confidence</th>
                <th>Limits Confidence</th>
              </tr>
            </thead>
            <tbody>
              {domains.map((d, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500, whiteSpace: "nowrap" }}>{d.domain}</td>
                  <td style={{ fontStyle: "italic", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {d.confidence_descriptor ?? "—"}
                  </td>
                  <td style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {d.supporting_factors?.length > 0 ? d.supporting_factors.join(" · ") : "—"}
                  </td>
                  <td style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {d.limiting_factors?.length > 0 ? d.limiting_factors.join(" · ") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {domains.length === 0 && (
        <p style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>No confidence assessment available.</p>
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

// ── Contradictions Section ───────────────────────────────────────────────────

type Contradiction = {
  contradiction_type: string;
  description: string;
  location_a: string;
  value_a: string;
  location_b: string;
  value_b: string;
  correct_value?: string | null;
  severity: "critical" | "significant" | "minor";
  economic_impact: "positive" | "negative" | "neutral" | "mixed" | "unknown";
  resolution_required: string;
};

type ArithmeticError = {
  field: string;
  stated_value: string;
  calculated_value: string;
  formula_used: string;
  discrepancy_pct?: number | null;
};


const CONTRADICTION_TYPE_LABEL: Record<string, string> = {
  numeric_mismatch:       "Numeric mismatch",
  arithmetic_error:       "Arithmetic error",
  logical_inconsistency:  "Logical inconsistency",
  temporal_inconsistency: "Temporal inconsistency",
  classification_mismatch:"Classification mismatch",
};

function ContradictionsSection({ data }: { data: Record<string, unknown> }) {
  const contradictions = (data.contradictions as Contradiction[]) ?? [];
  const arithmeticErrors = (data.arithmetic_errors as ArithmeticError[]) ?? [];
  const overall = data.overall_consistency_comment as string | undefined;

  const typeLabel = (t: string) =>
    CONTRADICTION_TYPE_LABEL[t] ?? t?.replace(/_/g, " ") ?? "Issue";

  return (
    <div className="report-specialist-body">
      {overall && <p style={{ lineHeight: 1.85, marginBottom: 24 }}>{overall}</p>}

      {arithmeticErrors.length > 0 && (
        <>
          <div className="report-sub-label">Arithmetic Errors</div>
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <table className="report-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Stated Value</th>
                  <th>Calculated Value</th>
                  <th>Formula Used</th>
                  <th>Discrepancy</th>
                </tr>
              </thead>
              <tbody>
                {arithmeticErrors.map((e, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{e.field}</td>
                    <td>{e.stated_value}</td>
                    <td>{e.calculated_value}</td>
                    <td style={{ fontFamily: "monospace", fontSize: 12 }}>{e.formula_used}</td>
                    <td>{e.discrepancy_pct != null ? `${e.discrepancy_pct.toFixed(1)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {contradictions.length > 0 && (
        <>
          {arithmeticErrors.length > 0 && <div className="report-sub-label" style={{ marginTop: 36 }}>Contradictions</div>}
          {contradictions.map((c, i) => (
            <div key={i} style={{
              paddingBottom: 24, marginBottom: 24,
              borderBottom: i < contradictions.length - 1 ? "1px solid var(--border)" : "none",
            }}>
              <p style={{ margin: "0 0 8px", fontSize: 14, lineHeight: 1.7 }}>
                <span style={{ fontWeight: 600 }}>{typeLabel(c.contradiction_type)}</span>
                {c.economic_impact && c.economic_impact !== "unknown" && (
                  <span style={{ color: "var(--text-tertiary)", fontWeight: 400 }}> · {c.economic_impact} economic impact</span>
                )}
                {c.severity === "critical" || c.severity === "significant" ? (
                  <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}> · {c.severity}</span>
                ) : null}
                {": "}
                {c.description}
              </p>
              <p style={{ margin: "0 0 6px", fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {c.location_a} states <em>"{c.value_a}"</em>; {c.location_b} states <em>"{c.value_b}"</em>.
                {c.correct_value ? ` The correct value is ${c.correct_value}.` : ""}
              </p>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
                Resolution required: {c.resolution_required}
              </p>
            </div>
          ))}
        </>
      )}

      {contradictions.length === 0 && arithmeticErrors.length === 0 && (
        <p style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>
          No contradictions or arithmetic errors identified.
        </p>
      )}
    </div>
  );
}

// ── Citations Section ────────────────────────────────────────────────────────

type Citation = {
  citation_id: string;
  section: string;
  claim: string;
  source_file: string;
  source_quote: string;
  location_in_source?: string | null;
  confidence: "direct" | "inferred" | "not_found";
};

const SECTION_LABEL: Record<string, string> = {
  "03_geology":   "Geology & Resources",
  "04_economics": "Economics",
  "05_risks":     "Risks",
  "06_dcf_model": "DCF Model",
  "07_assembly":  "Analyst Narrative",
  "08_data_gaps": "Data Gaps",
};


function CitationsSection({ data }: { data: Record<string, unknown> }) {
  const citations = (data.citations as Citation[]) ?? [];
  const comment = data.citation_coverage_comment as string | undefined;
  const uncited = (data.uncited_sections as string[]) ?? [];
  const notFound = data.not_found_count as number | undefined;

  const confLabel: Record<string, string> = {
    direct: "Direct",
    inferred: "Inferred",
    not_found: "Not found",
  };

  return (
    <div className="report-specialist-body">
      {comment && <p style={{ lineHeight: 1.85, marginBottom: 20 }}>{comment}</p>}

      {uncited.length > 0 && (
        <p style={{ fontSize: 13.5, color: "var(--text-secondary)", marginBottom: 16, lineHeight: 1.7 }}>
          The following sections had no traceable citations: {uncited.map((s) => SECTION_LABEL[s] ?? s).join(", ")}.
        </p>
      )}
      {notFound != null && notFound > 0 && (
        <p style={{ fontSize: 13.5, color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.7 }}>
          {notFound} claim{notFound !== 1 ? "s" : ""} could not be traced to a specific passage in the source documents and warrant analyst review.
        </p>
      )}

      {citations.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table className="report-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>Ref</th>
                <th>Section</th>
                <th>Claim</th>
                <th>Source</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {citations.map((c, i) => (
                <tr key={c.citation_id ?? i}>
                  <td style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)" }}>{c.citation_id}</td>
                  <td style={{ whiteSpace: "nowrap", color: "var(--text-secondary)", fontSize: 12 }}>{SECTION_LABEL[c.section] ?? c.section}</td>
                  <td style={{ lineHeight: 1.55 }}>{c.claim}</td>
                  <td style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {c.confidence !== "not_found" ? (
                      <>
                        <span style={{ fontWeight: 500 }}>{c.source_file}</span>
                        {c.location_in_source && <span style={{ color: "var(--text-tertiary)" }}> — {c.location_in_source}</span>}
                        {c.source_quote && <><br /><em style={{ fontSize: 11.5 }}>"{c.source_quote}"</em></>}
                      </>
                    ) : (
                      <em style={{ color: "var(--text-tertiary)" }}>Not found in source documents</em>
                    )}
                  </td>
                  <td style={{ whiteSpace: "nowrap", fontSize: 12, color: "var(--text-secondary)" }}>
                    {confLabel[c.confidence] ?? c.confidence}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ color: "var(--text-tertiary)", fontStyle: "italic" }}>No citations available for this run.</p>
      )}
    </div>
  );
}

// ── Compliance Section ────────────────────────────────────────────────────────

interface ComplianceCheck {
  category: string;
  requirement: string;
  status: "met" | "partial" | "missing" | "not_applicable";
  finding: string;
  recommendation?: string | null;
}

interface ComplianceQP {
  named: boolean;
  name?: string | null;
  credentials?: string | null;
  affiliation?: string | null;
  expertise_appropriate?: boolean | "unclear";
}


function ComplianceSection({ data }: { data: Record<string, unknown> }) {
  const overallStatus = (data.overall_status as string | undefined) ?? "major_gaps";
  const standard = (data.standard_applied_for_assessment as string | undefined) ?? "NI 43-101";
  const standardDetected = (data.standard_detected as string | undefined) ?? "unclear";
  const summary = data.overall_summary as string | undefined;
  const qp = data.qualified_person as ComplianceQP | undefined;
  const studyType = data.study_type as string | undefined;
  const studyMatch = data.study_type_resource_match as string | undefined;
  const studyMatchNote = data.study_type_resource_match_note as string | undefined;
  const checks = (data.checks as ComplianceCheck[] | undefined) ?? [];
  const criticalGaps = (data.critical_gaps as string[] | undefined) ?? [];
  const minorGaps = (data.minor_gaps as string[] | undefined) ?? [];

  const statusText: Record<string, string> = {
    compliant: "compliant",
    likely_compliant: "likely compliant, with only minor items identified",
    deficiencies_found: "found to have deficiencies requiring attention",
    major_gaps: "found to have major gaps",
  };

  const visibleChecks = checks.filter((c) => c.status !== "not_applicable");

  const statusSymbol = (s: string) => {
    if (s === "met") return "✓";
    if (s === "partial") return "partial";
    if (s === "missing") return "missing";
    return "—";
  };

  return (
    <div className="report-specialist-body">
      {/* Prose overview */}
      <p style={{ lineHeight: 1.85, marginBottom: summary ? 8 : 24 }}>
        This report was assessed against{" "}
        <strong>{standard}</strong>
        {standardDetected !== standard && standardDetected !== "unclear"
          ? ` (reporting standard detected in source documents: ${standardDetected})`
          : ""}
        {" "}and was {statusText[overallStatus] ?? overallStatus}.
      </p>
      {summary && <p style={{ lineHeight: 1.85, marginBottom: 24, color: "var(--text-secondary)" }}>{summary}</p>}

      {/* QP / CP */}
      {qp && (
        <p style={{ lineHeight: 1.85, marginBottom: 24, fontSize: 14, color: "var(--text-secondary)" }}>
          {qp.named
            ? <>The qualified person named in this report is <strong>{qp.name ?? "unnamed"}</strong>
                {qp.credentials ? ` (${qp.credentials})` : ""}
                {qp.affiliation ? `, ${qp.affiliation}` : ""}.
                {qp.expertise_appropriate === false ? " Note: the expertise listed may not be appropriate for this commodity and study type." : ""}
              </>
            : "No qualified person was identified in the source documents."}
          {studyType && studyMatch && studyMatch !== "not_applicable" && (
            <>{" "}The study is classified as a <strong>{studyType.toUpperCase()}</strong>; the resource classification is {
              studyMatch === "ok" ? "consistent with this study stage" :
              studyMatch === "concern" ? "a potential concern for this study stage" :
              "inconsistent with this study stage"
            }{studyMatchNote ? `: ${studyMatchNote}` : "."}</>
          )}
        </p>
      )}

      {/* Compliance checks table */}
      {visibleChecks.length > 0 && (
        <>
          <div className="report-sub-label">Compliance Checklist</div>
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <table className="report-table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>Status</th>
                  <th>Requirement</th>
                  <th>Finding</th>
                  <th>Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {visibleChecks.map((c, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500, whiteSpace: "nowrap", color: c.status === "met" ? "var(--success)" : "var(--text-secondary)" }}>
                      {statusSymbol(c.status)}
                    </td>
                    <td style={{ fontWeight: 500, lineHeight: 1.5 }}>{c.requirement}</td>
                    <td style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>{c.finding}</td>
                    <td style={{ color: "var(--text-secondary)", lineHeight: 1.5, fontStyle: "italic" }}>
                      {c.recommendation && c.status !== "met" ? c.recommendation : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Critical gaps */}
      {criticalGaps.length > 0 && (
        <>
          <div className="report-sub-label" style={{ marginTop: 36 }}>Critical Gaps</div>
          <ul style={{ margin: "12px 0 0", paddingLeft: 20, lineHeight: 1.85, color: "var(--text-primary)", fontSize: 14 }}>
            {criticalGaps.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </>
      )}

      {/* Minor gaps */}
      {minorGaps.length > 0 && (
        <>
          <div className="report-sub-label" style={{ marginTop: 36 }}>Minor Gaps</div>
          <ul style={{ margin: "12px 0 0", paddingLeft: 20, lineHeight: 1.85, color: "var(--text-secondary)", fontSize: 14 }}>
            {minorGaps.map((g, i) => <li key={i}>{g}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}

// ── Citation Panel ───────────────────────────────────────────────────────────

function CitationPanel({
  sectionKey,
  citations,
  projectId,
  onClose,
}: {
  sectionKey: string;
  citations: Citation[];
  projectId: string;
  onClose: () => void;
}) {
  const confLabel: Record<string, string> = { direct: "Direct", inferred: "Inferred", not_found: "Not found" };
  const title = SECTION_LABEL[sectionKey] ?? sectionKey.replace(/_/g, " ");

  return (
    <>
      <div className="citation-panel-overlay" onClick={onClose} />
      <aside className="citation-panel">
        <div className="citation-panel-header">
          <div>
            <div className="citation-panel-title">{title}</div>
            <div className="citation-panel-count">
              {citations.length} source{citations.length !== 1 ? "s" : ""}
            </div>
          </div>
          <button className="citation-panel-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="citation-panel-body">
          {citations.map((c) => (
            <div key={c.citation_id} className="citation-card">
              <div className="citation-card-top">
                <span className={`conf-dot conf-${c.confidence}`} title={confLabel[c.confidence]} />
                <span className="citation-card-id">{c.citation_id}</span>
                <span className="citation-card-file">{c.source_file}</span>
              </div>
              {c.location_in_source && (
                <div className="citation-card-location">{c.location_in_source}</div>
              )}
              <div className="citation-card-claim">{c.claim}</div>
              {c.confidence !== "not_found" && c.source_quote && (
                <div className="citation-quote">"{c.source_quote}"</div>
              )}
              {c.confidence !== "not_found" ? (
                <a
                  className="citation-source-link"
                  href={`${API_BASE}/projects/${projectId}/files/${encodeURIComponent(c.source_file)}/content`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open source →
                </a>
              ) : (
                <div className="citation-not-found">Could not be traced to a source document</div>
              )}
            </div>
          ))}
        </div>
      </aside>
    </>
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
  "09_confidence":      { title: "Confidence Assessment", subtitle: "How much trust to place in each section of this report", layer: "detail", number: "6" },
  "10_contradictions":  { title: "Contradiction & Consistency Check", subtitle: "Internal contradictions, numeric mismatches, and arithmetic errors", layer: "detail", number: "7" },
  "13_compliance":      { title: "NI 43-101 / JORC Compliance Check", subtitle: "Assessment against NI 43-101 and JORC Code 2012 reporting requirements", layer: "detail", number: "8" },
  "00_data_sources":    { title: "Appendix A — Source Documents", subtitle: "All documents used in this analysis", layer: "appendix" },
  "11_citations":       { title: "Appendix B — Source Citations", subtitle: "Traceability index mapping report claims to source documents", layer: "hidden" },
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
  const navigate = useNavigate();
  const { toast } = useToast();
  const [report, setReport] = useState<ReportContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [scrollPct, setScrollPct] = useState(0);
  const [activeCitationSection, setActiveCitationSection] = useState<string | null>(null);
  const [warningDismissed, setWarningDismissed] = useState(false);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const containerRef = useRef<HTMLDivElement | null>(null);

  const id = projectId!;
  const rid = runId!;

  useEffect(() => {
    getReport(id, rid)
      .then(setReport)
      .catch((err) => toast(err.message ?? "Could not load report", "error"))
      .finally(() => setLoading(false));
  }, [id, rid]);

  // Scroll progress bar
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const pct = scrollHeight <= clientHeight ? 100 : (scrollTop / (scrollHeight - clientHeight)) * 100;
    setScrollPct(Math.min(100, Math.round(pct)));
  }, []);

  if (loading) {
    return (
      <div className="report-full" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="spinner" style={{ width: 28, height: 28, color: "var(--text-tertiary)" }} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="report-full" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="empty-state">
          <h3>Report not found</h3>
          <p>This run may still be in progress or may have failed.</p>
          <Link to={`/projects/${id}`} className="btn btn-secondary" style={{ marginTop: 8 }}>
            Back to Project
          </Link>
        </div>
      </div>
    );
  }

  const sections = report.sections;
  const projectName = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // Citation data — sourced from 11_citations section
  const allCitations = useMemo(() => {
    const citData = sections["11_citations"] as Record<string, unknown> | undefined;
    return (citData?.citations as Citation[]) ?? [];
  }, [sections]);

  const citationsBySection = useMemo(() => {
    const map: Record<string, Citation[]> = {};
    for (const c of allCitations) {
      (map[c.section] ??= []).push(c);
    }
    return map;
  }, [allCitations]);

  const notFoundCount = useMemo(
    () => allCitations.filter((c) => c.confidence === "not_found").length,
    [allCitations]
  );
  const generatedAt = new Date().toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });

  // Order and categorise sections
  const orderedKeys = Object.keys(sections).sort();
  const narrativeKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "narrative");
  const detailKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "detail");
  const appendixKeys = orderedKeys.filter((k) => SECTION_CONFIG[k]?.layer === "appendix");

  const renderSection = (key: string) => {
    const content = sections[key];
    if (key === "00_data_sources") {
      return <DataSourcesSection projectId={id} data={content as Record<string, unknown>} />;
    }
    if (key === "06_dcf_model") {
      return <DcfSection data={content as Record<string, unknown>} />;
    }
    if (key === "07_assembly") {
      return <NarrativeSection assembly={content as Record<string, unknown>} projectId={id} />;
    }
    if (key === "08_data_gaps") {
      return <DataGapSection data={content as Record<string, unknown>} />;
    }
    if (key === "09_confidence") {
      return <ConfidenceSection data={content as Record<string, unknown>} />;
    }
    if (key === "10_contradictions") {
      return <ContradictionsSection data={content as Record<string, unknown>} />;
    }
    if (key === "11_citations") {
      return <CitationsSection data={content as Record<string, unknown>} />;
    }
    if (key === "13_compliance") {
      return <ComplianceSection data={content as Record<string, unknown>} />;
    }
    if (typeof content === "object" && content !== null && !Array.isArray(content)) {
      return <SpecialistSection data={content as Record<string, unknown>} projectId={id} />;
    }
    return <pre style={{ fontSize: 12, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
  };

  return (
    <div className="report-full" ref={containerRef} onScroll={handleScroll}>
      {/* Scroll progress bar */}
      <div className="report-progress-bar" style={{ width: `${scrollPct}%` }} />

      {/* Not-found citation warning */}
      {notFoundCount > 0 && !warningDismissed && (
        <div className="citation-warning-banner">
          <span>
            ⚠ {notFoundCount} claim{notFoundCount !== 1 ? "s" : ""} could not be traced to a
            source document — review before relying on this report.
          </span>
          <button className="citation-warning-dismiss" onClick={() => setWarningDismissed(true)}>
            Dismiss
          </button>
        </div>
      )}

      {/* Citation panel overlay */}
      {activeCitationSection && (
        <CitationPanel
          sectionKey={activeCitationSection}
          citations={citationsBySection[activeCitationSection] ?? []}
          projectId={id}
          onClose={() => setActiveCitationSection(null)}
        />
      )}

      {/* Top bar */}
      <div className="report-topbar">
        <button className="report-back-btn" onClick={() => navigate(`/projects/${id}`)}>
          <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
          Back to project
        </button>
        <div className="report-topbar-title">{projectName}</div>
        <div className="report-topbar-actions">
          <button className="btn btn-primary btn-sm" onClick={() => downloadReport(id, rid, "pdf")}>
            <DownloadIcon /> PDF
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "pptx")}>
            <DownloadIcon /> PPT
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "md")}>
            <DownloadIcon /> MD
          </button>
        </div>
      </div>

      {/* Article column */}
      <div className="report-article">
        {/* Cover */}
        <div className="report-cover">
          <div className="report-cover-eyebrow">Extract · Technical Analysis Report</div>
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
              ["Date", generatedAt],
              ["Run", rid.replace("run_", "")],
              ["Classification", "Internal"],
              ["Prepared by", "Extract AI"],
            ].map(([label, value]) => (
              <div key={label} className="report-cover-meta-item">
                <div className="report-cover-meta-label">{label}</div>
                <div className="report-cover-meta-value">{value}</div>
              </div>
            ))}
          </div>
          <div className="report-disclaimer">
            AI-generated for internal research only. Not investment advice. Verify against source documents.
          </div>
          <div className="report-export-row">
            <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {detailKeys.length} sections · {(sections["00_data_sources"] as any)?.file_count ?? 0} source documents
            </span>
            <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "json")}>
              <DownloadIcon /> JSON
            </button>
          </div>
        </div>

        {/* Narrative layer */}
        {narrativeKeys.map((key) => (
          <div key={key} id={key} ref={(el) => { sectionRefs.current[key] = el; }} className="report-narrative-wrapper">
            {renderSection(key)}
          </div>
        ))}

        {/* Detailed sections */}
        {detailKeys.length > 0 && <div className="report-section-divider" />}
        {detailKeys.map((key) => {
          const cfg = SECTION_CONFIG[key];
          const sectionCitations = citationsBySection[key];
          return (
            <div key={key} id={key} ref={(el) => { sectionRefs.current[key] = el; }} className="report-section">
              <div className="report-section-header">
                <div className="report-section-heading">
                  <div className="report-section-title-row">
                    <div className="report-section-title">{cfg?.title ?? key}</div>
                    {sectionCitations?.length > 0 && (
                      <button
                        className="citation-badge"
                        onClick={() => setActiveCitationSection(key)}
                        title="View source citations"
                      >
                        {sectionCitations.length} {sectionCitations.length === 1 ? "source" : "sources"}
                      </button>
                    )}
                  </div>
                  {cfg?.subtitle && <div className="report-section-subtitle">{cfg.subtitle}</div>}
                </div>
              </div>
              {renderSection(key)}
            </div>
          );
        })}

        {/* Appendix */}
        {appendixKeys.length > 0 && <div className="report-section-divider" />}
        {appendixKeys.map((key) => {
          const cfg = SECTION_CONFIG[key];
          return (
            <div key={key} id={key} ref={(el) => { sectionRefs.current[key] = el; }} className="report-section report-section--appendix">
              <div className="report-section-header">
                <div className="report-section-heading">
                  <div className="report-section-title">{cfg?.title ?? key}</div>
                  {cfg?.subtitle && <div className="report-section-subtitle">{cfg.subtitle}</div>}
                </div>
              </div>
              {renderSection(key)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
