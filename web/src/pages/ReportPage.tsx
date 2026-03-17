import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { exportUrl, getReport } from "../api/client";
import { useToast } from "../components/shared/Toast";
import type { ReportContent } from "../types";

// ── Icons ──────────────────────────────────────────────────────────────────

function DownloadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  );
}

// ── Section Renderers ──────────────────────────────────────────────────────

function renderValue(value: unknown, depth = 0): React.ReactNode {
  if (value === null || value === undefined) return <span style={{ color: "var(--text-tertiary)" }}>—</span>;
  if (typeof value === "string") return <span>{value}</span>;
  if (typeof value === "number") return <span style={{ fontWeight: 600 }}>{value}</span>;
  if (typeof value === "boolean") return <span style={{ fontWeight: 500 }}>{value ? "Yes" : "No"}</span>;

  if (Array.isArray(value)) {
    if (value.length === 0) return <span style={{ color: "var(--text-tertiary)" }}>None</span>;
    return (
      <ul className="report-list">
        {value.map((item, i) => (
          <li key={i} className="report-list-item">
            {typeof item === "object" && item !== null ? (
              <ObjectBlock obj={item as Record<string, unknown>} />
            ) : (
              String(item)
            )}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === "object") {
    return <ObjectBlock obj={value as Record<string, unknown>} />;
  }
  return String(value);
}

function ObjectBlock({ obj }: { obj: Record<string, unknown> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Object.entries(obj).map(([k, v]) => (
        <div key={k} className="report-field">
          <div className="report-field-label">{k.replace(/_/g, " ")}</div>
          <div className="report-field-value">{renderValue(v, 1)}</div>
        </div>
      ))}
    </div>
  );
}

// Section title mapping
const SECTION_TITLES: Record<string, string> = {
  project_facts: "Project Facts",
  geology_summary: "Geology",
  economics_summary: "Economics",
  risk_summary: "Risks",
  permitting_summary: "Permitting",
  financing_risk: "Financing Risk",
  contradictions: "Internal Contradictions",
  missing_data: "Data Gaps",
  assumptions: "Assumption Challenges",
  geology_score: "Geology Score",
  economics_score: "Economics Score",
  financing_score: "Financing Score",
  permitting_score: "Permitting Score",
  overall_score: "Overall Project Score",
};

// Score section — special display
function ScoreSection({ data }: { data: Record<string, unknown> }) {
  const score = (data.score ?? data.overall_score ?? data.rating) as number | undefined;
  const maxScore = 100;
  let scoreClass = "low";
  if (typeof score === "number") {
    if (score >= 70) scoreClass = "high";
    else if (score >= 45) scoreClass = "mid";
  }

  return (
    <div>
      {typeof score === "number" && (
        <div className="score-display">
          <div>
            <div className={`score-number ${scoreClass}`}>{score}</div>
            <div className="score-label">out of {maxScore}</div>
          </div>
          <div style={{ flex: 1 }}>
            <div className="progress-bar" style={{ height: 8 }}>
              <div
                className="progress-bar-fill"
                style={{
                  width: `${(score / maxScore) * 100}%`,
                  background: scoreClass === "high" ? "var(--success)" : scoreClass === "mid" ? "var(--warning)" : "var(--danger)",
                }}
              />
            </div>
          </div>
        </div>
      )}
      <ObjectBlock obj={Object.fromEntries(Object.entries(data).filter(([k]) => k !== "score" && k !== "overall_score" && k !== "rating"))} />
    </div>
  );
}

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

  const sectionCount = Object.keys(report.sections).length;
  const generatedAt = new Date().toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric"
  });

  return (
    <div className="report-container">
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/projects">Projects</Link>
        <span className="breadcrumb-sep">/</span>
        <Link to={`/projects/${id}`}>{id}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Report</span>
      </div>

      {/* Export bar */}
      <div className="export-bar">
        <div>
          <div className="export-bar-title">Analysis Report — {id}</div>
          <div className="export-bar-meta">
            Run: {rid} · {sectionCount} section{sectionCount !== 1 ? "s" : ""} · Generated {generatedAt}
          </div>
        </div>
        <div className="export-actions">
          <a
            href={exportUrl(id, rid, "md")}
            className="btn btn-secondary btn-sm"
            download
          >
            <DownloadIcon /> Markdown
          </a>
          <a
            href={exportUrl(id, rid, "txt")}
            className="btn btn-secondary btn-sm"
            download
          >
            <DownloadIcon /> Text
          </a>
          <a
            href={exportUrl(id, rid, "json")}
            className="btn btn-secondary btn-sm"
            download
          >
            <DownloadIcon /> JSON
          </a>
        </div>
      </div>

      {/* Report header */}
      <div className="report-header">
        <div className="report-title">Mining Project Analysis</div>
        <div className="report-meta">
          <div className="report-meta-item">
            <strong>Project:</strong> {id.replace(/_/g, " ")}
          </div>
          <div className="report-meta-item">
            <strong>Run ID:</strong> {rid}
          </div>
          <div className="report-meta-item">
            <strong>Date:</strong> {generatedAt}
          </div>
        </div>
        <div style={{ marginTop: 12, padding: "10px 16px", background: "var(--surface-2)", borderRadius: 8, fontSize: 12.5, color: "var(--text-secondary)", borderLeft: "3px solid var(--accent)" }}>
          This report is generated by an AI system for internal research purposes only. It does not constitute investment advice or a formal technical study. All data should be verified against primary source documents.
        </div>
      </div>

      {/* Sections */}
      {Object.entries(report.sections).map(([key, content]) => {
        const title = SECTION_TITLES[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        const isScore = key.includes("score");

        return (
          <div key={key} className="report-section">
            <div className="report-section-title">{title}</div>
            {isScore && typeof content === "object" && content !== null ? (
              <ScoreSection data={content as Record<string, unknown>} />
            ) : (
              renderValue(content)
            )}
          </div>
        );
      })}
    </div>
  );
}
