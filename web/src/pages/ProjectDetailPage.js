import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { deleteFile, getProject, getRun, listFiles, listRuns, startAnalysis, uploadFiles, } from "../api/client";
import DropZone from "../components/shared/DropZone";
import { useToast } from "../components/shared/Toast";
// ── Icons ──────────────────────────────────────────────────────────────────
function FileIcon() {
    return (_jsx("svg", { className: "file-icon", viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { fillRule: "evenodd", d: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z", clipRule: "evenodd" }) }));
}
function TrashIcon() {
    return (_jsx("svg", { width: "14", height: "14", viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { fillRule: "evenodd", d: "M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z", clipRule: "evenodd" }) }));
}
function PlayIcon() {
    return (_jsx("svg", { width: "16", height: "16", viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { fillRule: "evenodd", d: "M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z", clipRule: "evenodd" }) }));
}
// ── Helpers ────────────────────────────────────────────────────────────────
function formatBytes(b) {
    if (b < 1024)
        return `${b} B`;
    if (b < 1024 * 1024)
        return `${(b / 1024).toFixed(0)} KB`;
    return `${(b / 1024 / 1024).toFixed(1)} MB`;
}
function RunBadge({ status }) {
    const label = {
        pending: "Queued",
        running: "Running",
        complete: "Complete",
        failed: "Failed",
    };
    const cls = {
        pending: "badge-pending",
        running: "badge-running",
        complete: "badge-complete",
        failed: "badge-error",
    };
    return _jsx("span", { className: `badge ${cls[status] ?? "badge-pending"}`, children: label[status] ?? status });
}
// ── Main Page ──────────────────────────────────────────────────────────────
export default function ProjectDetailPage() {
    const { projectId } = useParams();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [project, setProject] = useState(null);
    const [files, setFiles] = useState([]);
    const [runs, setRuns] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [activeTab, setActiveTab] = useState("files");
    const pollRef = useRef(null);
    const id = projectId;
    useEffect(() => {
        Promise.all([
            getProject(id),
            listFiles(id),
            listRuns(id),
        ]).then(([p, f, r]) => {
            setProject(p);
            setFiles(f);
            setRuns(r);
        }).catch(() => {
            toast("Could not load project", "error");
        });
        return () => { if (pollRef.current)
            clearInterval(pollRef.current); };
    }, [id]);
    // Poll active run for status updates
    function startPolling(runId) {
        if (pollRef.current)
            clearInterval(pollRef.current);
        pollRef.current = setInterval(async () => {
            try {
                const updated = await getRun(id, runId);
                setRuns((prev) => prev.map((r) => r.run_id === runId ? updated : r));
                if (updated.status === "complete" || updated.status === "failed") {
                    clearInterval(pollRef.current);
                    setAnalyzing(false);
                    if (updated.status === "complete") {
                        toast("Analysis complete! View your report.", "success");
                    }
                    else {
                        toast(`Analysis failed: ${updated.error ?? "Unknown error"}`, "error");
                    }
                }
            }
            catch {
                clearInterval(pollRef.current);
                setAnalyzing(false);
            }
        }, 2000);
    }
    async function handleUpload(newFiles) {
        setUploading(true);
        try {
            const result = await uploadFiles(id, newFiles);
            toast(`${result.queued.length} file(s) uploaded`, "success");
            if (result.skipped.length)
                toast(`${result.skipped.length} file(s) skipped (unsupported type)`, "info");
            const updated = await listFiles(id);
            setFiles(updated);
        }
        catch (err) {
            toast(err.message ?? "Upload failed", "error");
        }
        finally {
            setUploading(false);
        }
    }
    async function handleDeleteFile(filename) {
        try {
            await deleteFile(id, filename);
            setFiles((prev) => prev.filter((f) => f.filename !== filename));
            toast(`Removed ${filename}`, "info");
        }
        catch {
            toast("Failed to remove file", "error");
        }
    }
    async function handleRunAnalysis() {
        if (files.length === 0) {
            toast("Upload files first before running analysis", "error");
            return;
        }
        setAnalyzing(true);
        try {
            const run = await startAnalysis(id);
            setRuns((prev) => [run, ...prev]);
            setActiveTab("runs");
            startPolling(run.run_id);
            toast("Analysis started — this may take 1–3 minutes", "info");
        }
        catch (err) {
            toast(err.message ?? "Failed to start analysis", "error");
            setAnalyzing(false);
        }
    }
    if (!project) {
        return (_jsx("div", { style: { textAlign: "center", padding: "80px 0" }, children: _jsx("span", { className: "spinner", style: { width: 28, height: 28, color: "var(--text-tertiary)" } }) }));
    }
    const activeRun = runs.find((r) => r.status === "running" || r.status === "pending");
    const completeRuns = runs.filter((r) => r.status === "complete");
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "breadcrumb", children: [_jsx(Link, { to: "/projects", children: "Projects" }), _jsx("span", { className: "breadcrumb-sep", children: "/" }), _jsx("span", { children: project.name })] }), _jsxs("div", { className: "page-header", children: [_jsxs("div", { children: [_jsx("h2", { children: project.name }), _jsxs("p", { children: [project.commodity && _jsxs("span", { children: [project.commodity, " \u00B7 "] }), project.study_type, project.description && _jsxs("span", { children: [" \u00B7 ", project.description] })] })] }), _jsx("button", { className: "btn btn-primary btn-lg", onClick: handleRunAnalysis, disabled: analyzing || files.length === 0, children: analyzing ? (_jsxs(_Fragment, { children: [_jsx("span", { className: "spinner" }), " Analyzing\u2026"] })) : (_jsxs(_Fragment, { children: [_jsx(PlayIcon, {}), " Run Analysis"] })) })] }), activeRun && (_jsx("div", { style: { marginBottom: 24 }, children: _jsxs("div", { className: "run-panel", children: [_jsxs("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }, children: [_jsx("span", { style: { fontSize: 14, fontWeight: 600 }, children: "Analysis in progress" }), _jsx(RunBadge, { status: activeRun.status })] }), _jsx("div", { className: "progress-bar progress-bar-indeterminate", children: _jsx("div", { className: "progress-bar-fill" }) }), _jsxs("div", { style: { marginTop: 8, fontSize: 13, color: "var(--text-secondary)" }, children: ["Step: ", activeRun.step ?? "queued"] })] }) })), completeRuns.length > 0 && (_jsxs("div", { className: "card", style: { marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }, children: [_jsxs("div", { children: [_jsxs("div", { style: { fontWeight: 600 }, children: [completeRuns.length, " report", completeRuns.length > 1 ? "s" : "", " ready"] }), _jsx("div", { style: { fontSize: 13, color: "var(--text-secondary)", marginTop: 3 }, children: "Click to view the most recent analysis results" })] }), _jsx(Link, { to: `/projects/${id}/report/${completeRuns[0].run_id}`, className: "btn btn-primary", children: "View Report" })] })), _jsxs("div", { className: "tabs", children: [_jsxs("button", { className: `tab ${activeTab === "files" ? "active" : ""}`, onClick: () => setActiveTab("files"), children: ["Files (", files.length, ")"] }), _jsxs("button", { className: `tab ${activeTab === "runs" ? "active" : ""}`, onClick: () => setActiveTab("runs"), children: ["Runs (", runs.length, ")"] })] }), activeTab === "files" && (_jsxs(_Fragment, { children: [_jsx(DropZone, { onFiles: handleUpload, disabled: uploading }), uploading && (_jsxs("div", { style: { textAlign: "center", padding: "16px 0", color: "var(--text-secondary)", fontSize: 13 }, children: [_jsx("span", { className: "spinner", style: { width: 16, height: 16 } }), " Uploading\u2026"] })), files.length > 0 && (_jsxs("div", { style: { marginTop: 16 }, children: [_jsx("div", { className: "section-header", children: _jsxs("div", { className: "section-title", children: ["File Library (", files.length, ")"] }) }), _jsx("div", { className: "file-list", children: files.map((f) => (_jsxs("div", { className: "file-row", children: [_jsx(FileIcon, {}), _jsx("span", { className: "file-name", children: f.filename }), _jsx("span", { className: "file-size", children: formatBytes(f.size_bytes) }), _jsx("button", { className: "btn-icon-only", onClick: () => handleDeleteFile(f.filename), title: "Remove file", children: _jsx(TrashIcon, {}) })] }, f.filename))) })] })), files.length === 0 && !uploading && (_jsx("div", { style: { textAlign: "center", padding: "20px", color: "var(--text-secondary)", fontSize: 13 }, children: "No files yet \u2014 drop your documents above to get started" }))] })), activeTab === "runs" && (_jsx(_Fragment, { children: runs.length === 0 ? (_jsxs("div", { className: "empty-state", children: [_jsx("h3", { children: "No runs yet" }), _jsx("p", { children: "Upload files and click \"Run Analysis\" to generate your first report" })] })) : (_jsx("div", { className: "run-panel", children: runs.map((r) => (_jsxs("div", { className: "run-row", children: [_jsx(RunBadge, { status: r.status }), _jsx("span", { className: "run-id", children: r.run_id }), _jsx("span", { className: "run-step", children: r.error ?? r.step ?? "" }), _jsx("span", { className: "run-time", children: r.completed_at
                                    ? new Date(r.completed_at).toLocaleString()
                                    : r.started_at
                                        ? new Date(r.started_at).toLocaleString()
                                        : "" }), r.status === "complete" && (_jsx(Link, { to: `/projects/${id}/report/${r.run_id}`, className: "btn btn-secondary btn-sm", children: "View Report" }))] }, r.run_id))) })) }))] }));
}
