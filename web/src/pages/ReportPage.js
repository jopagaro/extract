import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { exportUrl, getReport } from "../api/client";
import { useToast } from "../components/shared/Toast";
// ── Icons ──────────────────────────────────────────────────────────────────
function DownloadIcon() {
    return (_jsx("svg", { width: "15", height: "15", viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { fillRule: "evenodd", d: "M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z", clipRule: "evenodd" }) }));
}
// ── Section Renderers ──────────────────────────────────────────────────────
function renderValue(value, depth = 0) {
    if (value === null || value === undefined)
        return _jsx("span", { style: { color: "var(--text-tertiary)" }, children: "\u2014" });
    if (typeof value === "string")
        return _jsx("span", { children: value });
    if (typeof value === "number")
        return _jsx("span", { style: { fontWeight: 600 }, children: value });
    if (typeof value === "boolean")
        return _jsx("span", { style: { fontWeight: 500 }, children: value ? "Yes" : "No" });
    if (Array.isArray(value)) {
        if (value.length === 0)
            return _jsx("span", { style: { color: "var(--text-tertiary)" }, children: "None" });
        return (_jsx("ul", { className: "report-list", children: value.map((item, i) => (_jsx("li", { className: "report-list-item", children: typeof item === "object" && item !== null ? (_jsx(ObjectBlock, { obj: item })) : (String(item)) }, i))) }));
    }
    if (typeof value === "object") {
        return _jsx(ObjectBlock, { obj: value });
    }
    return String(value);
}
function ObjectBlock({ obj }) {
    return (_jsx("div", { style: { display: "flex", flexDirection: "column", gap: 8 }, children: Object.entries(obj).map(([k, v]) => (_jsxs("div", { className: "report-field", children: [_jsx("div", { className: "report-field-label", children: k.replace(/_/g, " ") }), _jsx("div", { className: "report-field-value", children: renderValue(v, 1) })] }, k))) }));
}
// Section title mapping
const SECTION_TITLES = {
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
function ScoreSection({ data }) {
    const score = (data.score ?? data.overall_score ?? data.rating);
    const maxScore = 100;
    let scoreClass = "low";
    if (typeof score === "number") {
        if (score >= 70)
            scoreClass = "high";
        else if (score >= 45)
            scoreClass = "mid";
    }
    return (_jsxs("div", { children: [typeof score === "number" && (_jsxs("div", { className: "score-display", children: [_jsxs("div", { children: [_jsx("div", { className: `score-number ${scoreClass}`, children: score }), _jsxs("div", { className: "score-label", children: ["out of ", maxScore] })] }), _jsx("div", { style: { flex: 1 }, children: _jsx("div", { className: "progress-bar", style: { height: 8 }, children: _jsx("div", { className: "progress-bar-fill", style: {
                                    width: `${(score / maxScore) * 100}%`,
                                    background: scoreClass === "high" ? "var(--success)" : scoreClass === "mid" ? "var(--warning)" : "var(--danger)",
                                } }) }) })] })), _jsx(ObjectBlock, { obj: Object.fromEntries(Object.entries(data).filter(([k]) => k !== "score" && k !== "overall_score" && k !== "rating")) })] }));
}
// ── Report Page ────────────────────────────────────────────────────────────
export default function ReportPage() {
    const { projectId, runId } = useParams();
    const { toast } = useToast();
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const id = projectId;
    const rid = runId;
    useEffect(() => {
        getReport(id, rid)
            .then(setReport)
            .catch((err) => toast(err.message ?? "Could not load report", "error"))
            .finally(() => setLoading(false));
    }, [id, rid]);
    if (loading) {
        return (_jsx("div", { style: { textAlign: "center", padding: "80px 0" }, children: _jsx("span", { className: "spinner", style: { width: 28, height: 28, color: "var(--text-tertiary)" } }) }));
    }
    if (!report) {
        return (_jsxs("div", { className: "empty-state", children: [_jsx("h3", { children: "Report not found" }), _jsx("p", { children: "This run may still be in progress or may have failed." }), _jsx("br", {}), _jsx(Link, { to: `/projects/${id}`, className: "btn btn-secondary", style: { marginTop: 8 }, children: "Back to Project" })] }));
    }
    const sectionCount = Object.keys(report.sections).length;
    const generatedAt = new Date().toLocaleDateString("en-US", {
        month: "long", day: "numeric", year: "numeric"
    });
    return (_jsxs("div", { className: "report-container", children: [_jsxs("div", { className: "breadcrumb", children: [_jsx(Link, { to: "/projects", children: "Projects" }), _jsx("span", { className: "breadcrumb-sep", children: "/" }), _jsx(Link, { to: `/projects/${id}`, children: id }), _jsx("span", { className: "breadcrumb-sep", children: "/" }), _jsx("span", { children: "Report" })] }), _jsxs("div", { className: "export-bar", children: [_jsxs("div", { children: [_jsxs("div", { className: "export-bar-title", children: ["Analysis Report \u2014 ", id] }), _jsxs("div", { className: "export-bar-meta", children: ["Run: ", rid, " \u00B7 ", sectionCount, " section", sectionCount !== 1 ? "s" : "", " \u00B7 Generated ", generatedAt] })] }), _jsxs("div", { className: "export-actions", children: [_jsxs("a", { href: exportUrl(id, rid, "md"), className: "btn btn-secondary btn-sm", download: true, children: [_jsx(DownloadIcon, {}), " Markdown"] }), _jsxs("a", { href: exportUrl(id, rid, "txt"), className: "btn btn-secondary btn-sm", download: true, children: [_jsx(DownloadIcon, {}), " Text"] }), _jsxs("a", { href: exportUrl(id, rid, "json"), className: "btn btn-secondary btn-sm", download: true, children: [_jsx(DownloadIcon, {}), " JSON"] })] })] }), _jsxs("div", { className: "report-header", children: [_jsx("div", { className: "report-title", children: "Mining Project Analysis" }), _jsxs("div", { className: "report-meta", children: [_jsxs("div", { className: "report-meta-item", children: [_jsx("strong", { children: "Project:" }), " ", id.replace(/_/g, " ")] }), _jsxs("div", { className: "report-meta-item", children: [_jsx("strong", { children: "Run ID:" }), " ", rid] }), _jsxs("div", { className: "report-meta-item", children: [_jsx("strong", { children: "Date:" }), " ", generatedAt] })] }), _jsx("div", { style: { marginTop: 12, padding: "10px 16px", background: "var(--surface-2)", borderRadius: 8, fontSize: 12.5, color: "var(--text-secondary)", borderLeft: "3px solid var(--accent)" }, children: "This report is generated by an AI system for internal research purposes only. It does not constitute investment advice or a formal technical study. All data should be verified against primary source documents." })] }), Object.entries(report.sections).map(([key, content]) => {
                const title = SECTION_TITLES[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                const isScore = key.includes("score");
                return (_jsxs("div", { className: "report-section", children: [_jsx("div", { className: "report-section-title", children: title }), isScore && typeof content === "object" && content !== null ? (_jsx(ScoreSection, { data: content })) : (renderValue(content))] }, key));
            })] }));
}
