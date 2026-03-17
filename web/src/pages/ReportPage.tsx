import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { ReportContent } from "../types";

// ── Download helper ────────────────────────────────────────────────────────

async function downloadReport(
  projectId: string,
  runId: string,
  format: "json" | "md" | "txt" | "pdf"
) {
  const url = `/api/projects/${projectId}/reports/${runId}/export?format=${format}`;
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
    if (filePath) {
      await writeBinaryFile(filePath, new Uint8Array(buffer));
    }
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

// ── Icons ──────────────────────────────────────────────────────────────────

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

// ── Section renderers ──────────────────────────────────────────────────────

function ProseSection({ data }: { data: Record<string, unknown> }) {
  // Find all text fields and render them as flowing paragraphs
  const textKeys = Object.keys(data).filter(k =>
    typeof data[k] === "string" && (data[k] as string).length > 80
  );
  const tableKeys = Object.keys(data).filter(k => Array.isArray(data[k]));
  const scalarKeys = Object.keys(data).filter(k =>
    !textKeys.includes(k) && !tableKeys.includes(k) && data[k] !== null && data[k] !== undefined
  );

  return (
    <div>
      {/* Prose paragraphs */}
      {textKeys.map(k => (
        <div key={k} style={{ marginBottom: 20 }}>
          {textKeys.length > 1 && (
            <div style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 6,
            }}>
              {k.replace(/_/g, " ")}
            </div>
          )}
          <div style={{
            fontSize: 14.5,
            lineHeight: 1.75,
            color: "var(--text-primary)",
            whiteSpace: "pre-wrap",
          }}>
            {String(data[k])}
          </div>
        </div>
      ))}

      {/* Key metrics table */}
      {tableKeys.map(k => {
        const rows = data[k] as Record<string, unknown>[];
        if (!rows.length) return null;
        const cols = Object.keys(rows[0]);
        return (
          <div key={k} style={{ marginTop: 16, overflowX: "auto" }}>
            {tableKeys.length > 1 && (
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
                {k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
              </div>
            )}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--surface-2)" }}>
                  {cols.map(c => (
                    <th key={c} style={{
                      padding: "8px 12px",
                      textAlign: "left",
                      fontWeight: 600,
                      fontSize: 11.5,
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                      color: "var(--text-secondary)",
                      borderBottom: "2px solid var(--border)",
                    }}>
                      {c.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    {cols.map(c => (
                      <td key={c} style={{
                        padding: "8px 12px",
                        color: "var(--text-primary)",
                        fontSize: 13.5,
                      }}>
                        {row[c] === null || row[c] === undefined ? "—" : String(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}

      {/* Scalar metadata (small, at bottom) */}
      {scalarKeys.length > 0 && (
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px 24px",
          marginTop: 16,
          paddingTop: 12,
          borderTop: "1px solid var(--border)",
        }}>
          {scalarKeys.map(k => (
            <div key={k} style={{ fontSize: 12.5 }}>
              <span style={{ color: "var(--text-tertiary)", marginRight: 4 }}>
                {k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}:
              </span>
              <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                {String(data[k])}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DataSourcesSection({ data }: { data: Record<string, unknown> }) {
  const files = data.source_files as string[] ?? [];
  return (
    <div>
      <div style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderLeft: "4px solid var(--accent)",
        borderRadius: 8,
        padding: "14px 18px",
        marginBottom: 16,
        fontSize: 13.5,
        color: "var(--text-secondary)",
        lineHeight: 1.6,
      }}>
        {String(data.notice ?? "")}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
        Source Documents ({files.length})
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {files.map((f, i) => (
          <div key={i} style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 10px",
            background: "var(--surface-2)",
            borderRadius: 6,
            fontSize: 13,
            color: "var(--text-primary)",
          }}>
            <span style={{ color: "var(--accent)", fontSize: 11, fontWeight: 600 }}>✓</span>
            {f}
          </div>
        ))}
      </div>
      {data.generated_at && (
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 12 }}>
          Generated: {new Date(data.generated_at as string).toLocaleString()}
        </div>
      )}
    </div>
  );
}

function SectionContent({ sectionKey, content }: { sectionKey: string; content: unknown }) {
  if (sectionKey === "00_data_sources") {
    return <DataSourcesSection data={content as Record<string, unknown>} />;
  }
  if (typeof content === "object" && content !== null && !Array.isArray(content)) {
    return <ProseSection data={content as Record<string, unknown>} />;
  }
  if (typeof content === "string") {
    return <div style={{ fontSize: 14.5, lineHeight: 1.75, whiteSpace: "pre-wrap" }}>{content}</div>;
  }
  return <pre style={{ fontSize: 12, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
}

// ── Section config ─────────────────────────────────────────────────────────

const SECTION_META: Record<string, { title: string; subtitle?: string }> = {
  "00_data_sources": { title: "Data Sources & Notice", subtitle: "Documents used in this analysis" },
  "01_project_facts": { title: "Project Overview", subtitle: "Extracted project facts" },
  "02_executive_summary": { title: "Executive Summary", subtitle: "Key findings and economic highlights" },
  "03_geology": { title: "Geological Setting & Mineralisation", subtitle: "Deposit geology and resource assessment" },
  "04_economics": { title: "Economic Analysis", subtitle: "Financial projections and sensitivity" },
  "05_risks": { title: "Risks & Uncertainties", subtitle: "Material risks and mitigations" },
};

// ── Report Page ────────────────────────────────────────────────────────────

export default function ReportPage() {
  const { projectId, runId } = useParams<{ projectId: string; runId: string }>();
  const { toast } = useToast();
  const [report, setReport] = useState<ReportContent | null>(null);
  const [loading, setLoading] = useState(true);

  const id = projectId!;
  const rid = runId!;

  useEffect(() => {
    getReport(id, rid)
      .then(setReport)
      .catch((err) => toast(err.message ?? "Could not load report", "error"))
      .finally(() => setLoading(false));
  }, [id, rid]);

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
        <br />
        <Link to={`/projects/${id}`} className="btn btn-secondary" style={{ marginTop: 8 }}>
          Back to Project
        </Link>
      </div>
    );
  }

  const projectName = id.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  const generatedAt = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  const orderedSections = Object.entries(report.sections).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="report-container">
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/projects">Projects</Link>
        <span className="breadcrumb-sep">/</span>
        <Link to={`/projects/${id}`}>{projectName}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Report</span>
      </div>

      {/* Export bar */}
      <div className="export-bar">
        <div>
          <div className="export-bar-title">{projectName} — Technical Analysis Report</div>
          <div className="export-bar-meta">
            {orderedSections.length} sections · Run {rid} · {generatedAt}
          </div>
        </div>
        <div className="export-actions">
          <button className="btn btn-primary btn-sm" onClick={() => downloadReport(id, rid, "pdf")}>
            <DownloadIcon /> Export PDF
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "md")}>
            <DownloadIcon /> Markdown
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => downloadReport(id, rid, "json")}>
            <DownloadIcon /> JSON
          </button>
        </div>
      </div>

      {/* Report cover */}
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "36px 40px",
        marginBottom: 20,
        boxShadow: "var(--shadow)",
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)", marginBottom: 12 }}>
          Mining Intelligence Platform — Internal Research Report
        </div>
        <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.04em", marginBottom: 8, lineHeight: 1.1 }}>
          {projectName}
        </div>
        <div style={{ fontSize: 16, color: "var(--text-secondary)", marginBottom: 20 }}>
          Project Technical Analysis
        </div>
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
          {[
            ["Report Date", generatedAt],
            ["Run ID", rid],
            ["Classification", "Internal — Confidential"],
            ["Prepared By", "Mining Intelligence Platform AI"],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: 13.5, fontWeight: 500, color: "var(--text-primary)" }}>{value}</div>
            </div>
          ))}
        </div>
        <div style={{
          marginTop: 24,
          padding: "10px 16px",
          background: "#fff8ed",
          borderRadius: 8,
          fontSize: 12,
          color: "#b7570a",
          borderLeft: "3px solid #f0a500",
        }}>
          This report is generated by an AI system for internal research purposes only. It does not constitute investment advice or a formal technical study. All data should be verified against primary source documents.
        </div>
      </div>

      {/* Report sections */}
      {orderedSections.map(([key, content]) => {
        const meta = SECTION_META[key] ?? {
          title: key.replace(/^\d+_/, "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
        };
        return (
          <div key={key} className="report-section">
            <div style={{ marginBottom: 16 }}>
              <div className="report-section-title">{meta.title}</div>
              {meta.subtitle && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: -8 }}>
                  {meta.subtitle}
                </div>
              )}
            </div>
            <SectionContent sectionKey={key} content={content} />
          </div>
        );
      })}
    </div>
  );
}
