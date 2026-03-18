import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getReport } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { ReportContent } from "../types";

// ── Download ────────────────────────────────────────────────────────────────

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

// ── Section renderers ───────────────────────────────────────────────────────

function DataSourcesSection({ data }: { data: Record<string, unknown> }) {
  const files = (data.source_files as string[]) ?? [];
  return (
    <div>
      <div className="report-notice">
        {String(data.notice ?? "")}
      </div>
      {files.length > 0 && (
        <>
          <div className="report-sub-label">Source Documents ({files.length})</div>
          <div className="report-file-list">
            {files.map((f, i) => (
              <div key={i} className="report-file-row">
                <span className="report-file-check">✓</span>
                {f}
              </div>
            ))}
          </div>
        </>
      )}
      {data.generated_at != null && (
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 14 }}>
          Generated: {new Date(String(data.generated_at)).toLocaleString()}
        </div>
      )}
    </div>
  );
}

function ListBlock({ items, title }: { items: unknown[]; title?: string }) {
  if (!items.length) return null;

  // Array of objects → table
  if (typeof items[0] === "object" && items[0] !== null) {
    const cols = Object.keys(items[0] as object);
    return (
      <div style={{ marginTop: 20 }}>
        {title && <div className="report-sub-label">{title}</div>}
        <div style={{ overflowX: "auto" }}>
          <table className="report-table">
            <thead>
              <tr>
                {cols.map((c) => (
                  <th key={c}>{c.replace(/_/g, " ")}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(items as Record<string, unknown>[]).map((row, i) => (
                <tr key={i}>
                  {cols.map((c) => (
                    <td key={c}>
                      {row[c] === null || row[c] === undefined ? "—" : String(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Array of strings → clean bullet list
  return (
    <div style={{ marginTop: 20 }}>
      {title && <div className="report-sub-label">{title}</div>}
      <ul className="report-bullet-list">
        {items.map((item, i) => (
          <li key={i}>
            <span className="report-bullet">—</span>
            <span>{String(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProseSection({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);

  // Categorise fields
  const prose = entries.filter(([, v]) => typeof v === "string" && (v as string).length > 60);
  const lists = entries.filter(([, v]) => Array.isArray(v) && (v as unknown[]).length > 0);
  const scalars = entries.filter(
    ([k]) =>
      !prose.find(([pk]) => pk === k) &&
      !lists.find(([lk]) => lk === k)
  );

  const isSingleProse = prose.length === 1 && lists.length === 0 && scalars.length === 0;

  return (
    <div className="report-prose-block">
      {/* Prose paragraphs */}
      {prose.map(([k, v]) => (
        <div key={k} className="report-prose-para">
          {!isSingleProse && prose.length > 1 && (
            <div className="report-para-label">{k.replace(/_/g, " ")}</div>
          )}
          <p>{String(v)}</p>
        </div>
      ))}

      {/* Lists */}
      {lists.map(([k, v]) => (
        <ListBlock
          key={k}
          items={v as unknown[]}
          title={lists.length > 1 || prose.length > 0
            ? k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
            : undefined}
        />
      ))}

      {/* Scalar metadata — shown as subtle chips at the bottom */}
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
  if (sectionKey === "00_data_sources") {
    return <DataSourcesSection data={content as Record<string, unknown>} />;
  }
  if (typeof content === "object" && content !== null && !Array.isArray(content)) {
    return <ProseSection data={content as Record<string, unknown>} />;
  }
  if (typeof content === "string") {
    return (
      <div className="report-prose-block">
        <p>{content}</p>
      </div>
    );
  }
  return <pre style={{ fontSize: 12, overflow: "auto" }}>{JSON.stringify(content, null, 2)}</pre>;
}

// ── Section metadata ────────────────────────────────────────────────────────

const SECTION_META: Record<string, { title: string; subtitle?: string }> = {
  "00_data_sources": { title: "Data Sources", subtitle: "Documents used in this analysis" },
  "01_project_facts": { title: "Project Overview", subtitle: "Extracted project facts" },
  "02_executive_summary": { title: "Executive Summary", subtitle: "Key findings and highlights" },
  "03_geology": { title: "Geology", subtitle: "Deposit geology and resource assessment" },
  "04_economics": { title: "Economics", subtitle: "Financial projections and sensitivity" },
  "05_risks": { title: "Risks & Uncertainties", subtitle: "Material risks and mitigations" },
};

// ── Report Page ─────────────────────────────────────────────────────────────

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

  const projectName = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const generatedAt = new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
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

      {/* Cover card */}
      <div className="report-cover">
        <div className="report-cover-eyebrow">
          Extract — Technical Analysis Report
        </div>
        <div className="report-cover-title">{projectName}</div>
        <div className="report-cover-subtitle">Project Technical Analysis</div>

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
          This report is generated by an AI system for internal research purposes only. It does not
          constitute investment advice or a formal technical study. All data should be verified
          against primary source documents.
        </div>

        {/* Export actions */}
        <div className="report-export-row">
          <span style={{ fontSize: 12.5, color: "var(--text-tertiary)" }}>
            {orderedSections.length} sections
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

      {/* Report sections */}
      {orderedSections.map(([key, content]) => {
        const meta = SECTION_META[key] ?? {
          title: key
            .replace(/^\d+_/, "")
            .replace(/_/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase()),
        };
        return (
          <div key={key} className="report-section">
            <div className="report-section-header">
              <div className="report-section-title">{meta.title}</div>
              {meta.subtitle && (
                <div className="report-section-subtitle">{meta.subtitle}</div>
              )}
            </div>
            <SectionContent sectionKey={key} content={content} />
          </div>
        );
      })}
    </div>
  );
}
