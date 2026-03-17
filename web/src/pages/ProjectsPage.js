import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects } from "../api/client";
import { useToast } from "../components/shared/Toast";
// ── Icons ──────────────────────────────────────────────────────────────────
function PlusIcon() {
    return (_jsx("svg", { width: "16", height: "16", viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", children: _jsx("path", { d: "M8 3v10M3 8h10" }) }));
}
function MineIcon() {
    return (_jsxs("svg", { className: "empty-state-icon", viewBox: "0 0 52 52", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("circle", { cx: "26", cy: "26", r: "22" }), _jsx("path", { d: "M26 14v24M18 22l8-8 8 8", strokeLinecap: "round", strokeLinejoin: "round" })] }));
}
// ── Status Badge ───────────────────────────────────────────────────────────
function StatusBadge({ status }) {
    const labels = {
        empty: "Empty",
        ingested: "Files Ready",
        analyzed: "Analyzed",
        error: "Error",
    };
    return _jsx("span", { className: `badge badge-${status}`, children: labels[status] });
}
function CreateModal({ onClose, onCreate }) {
    const [form, setForm] = useState({
        name: "",
        description: "",
        commodity: "",
        study_type: "PEA",
    });
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();
    function set(field, value) {
        setForm((f) => ({ ...f, [field]: value }));
    }
    async function handleSubmit(e) {
        e.preventDefault();
        if (!form.name.trim())
            return;
        setLoading(true);
        try {
            const project = await createProject(form);
            onCreate(project);
            toast(`Project "${project.name}" created`, "success");
            onClose();
        }
        catch (err) {
            toast(err.message ?? "Failed to create project", "error");
        }
        finally {
            setLoading(false);
        }
    }
    return (_jsx("div", { className: "modal-overlay", onClick: (e) => e.target === e.currentTarget && onClose(), children: _jsxs("div", { className: "modal", children: [_jsx("div", { className: "modal-title", children: "New Project" }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("div", { className: "form-group", children: [_jsx("label", { className: "form-label", children: "Project Name *" }), _jsx("input", { className: "form-input", placeholder: "e.g. Blackwater Gold Project", value: form.name, onChange: (e) => set("name", e.target.value), autoFocus: true, required: true })] }), _jsxs("div", { className: "form-group", children: [_jsx("label", { className: "form-label", children: "Description" }), _jsx("textarea", { className: "form-textarea", placeholder: "Brief description of the project", value: form.description ?? "", onChange: (e) => set("description", e.target.value) })] }), _jsxs("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }, children: [_jsxs("div", { className: "form-group", children: [_jsx("label", { className: "form-label", children: "Primary Commodity" }), _jsx("input", { className: "form-input", placeholder: "Gold, Copper, Lithium...", value: form.commodity ?? "", onChange: (e) => set("commodity", e.target.value) })] }), _jsxs("div", { className: "form-group", children: [_jsx("label", { className: "form-label", children: "Study Type" }), _jsxs("select", { className: "form-select", value: form.study_type, onChange: (e) => set("study_type", e.target.value), children: [_jsx("option", { value: "PEA", children: "PEA" }), _jsx("option", { value: "PFS", children: "PFS" }), _jsx("option", { value: "FS", children: "FS" }), _jsx("option", { value: "scoping", children: "Scoping Study" }), _jsx("option", { value: "other", children: "Other" })] })] })] }), _jsxs("div", { className: "modal-footer", children: [_jsx("button", { type: "button", className: "btn btn-secondary", onClick: onClose, disabled: loading, children: "Cancel" }), _jsxs("button", { type: "submit", className: "btn btn-primary", disabled: loading || !form.name.trim(), children: [loading ? _jsx("span", { className: "spinner" }) : null, "Create Project"] })] })] })] }) }));
}
// ── Main Page ──────────────────────────────────────────────────────────────
export default function ProjectsPage() {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const { toast } = useToast();
    useEffect(() => {
        listProjects()
            .then(setProjects)
            .catch(() => toast("Could not load projects. Is the API server running?", "error"))
            .finally(() => setLoading(false));
    }, []);
    function formatDate(iso) {
        return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    }
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-header", children: [_jsxs("div", { children: [_jsx("h2", { children: "Projects" }), _jsx("p", { children: "Each project is one mining asset \u2014 upload documents and run analysis" })] }), _jsxs("button", { className: "btn btn-primary", onClick: () => setShowCreate(true), children: [_jsx(PlusIcon, {}), " New Project"] })] }), loading ? (_jsx("div", { style: { textAlign: "center", padding: "80px 0", color: "var(--text-secondary)" }, children: _jsx("span", { className: "spinner", style: { width: 28, height: 28 } }) })) : projects.length === 0 ? (_jsxs("div", { className: "empty-state", children: [_jsx(MineIcon, {}), _jsx("h3", { children: "No projects yet" }), _jsx("p", { children: "Create your first project to get started" }), _jsx("br", {}), _jsxs("button", { className: "btn btn-primary", onClick: () => setShowCreate(true), style: { marginTop: 8 }, children: [_jsx(PlusIcon, {}), " New Project"] })] })) : (_jsx("div", { className: "card-grid", children: projects.map((p) => (_jsxs(Link, { to: `/projects/${p.id}`, className: "project-card", children: [_jsxs("div", { className: "project-card-header", children: [_jsxs("div", { children: [_jsx("div", { className: "project-card-name", children: p.name }), _jsxs("div", { className: "project-card-meta", children: [p.commodity && _jsxs("span", { children: [p.commodity, " \u00B7 "] }), p.study_type, p.created_at && _jsxs("span", { children: [" \u00B7 ", formatDate(p.created_at)] })] })] }), _jsx(StatusBadge, { status: p.status })] }), p.description && (_jsx("div", { style: { fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }, children: p.description })), _jsxs("div", { className: "project-card-stats", children: [_jsxs("div", { className: "stat", children: [_jsx("div", { className: "stat-value", children: p.file_count }), _jsx("div", { className: "stat-label", children: "Files" })] }), _jsxs("div", { className: "stat", children: [_jsx("div", { className: "stat-value", children: p.run_count }), _jsx("div", { className: "stat-label", children: "Runs" })] })] })] }, p.id))) })), showCreate && (_jsx(CreateModal, { onClose: () => setShowCreate(false), onCreate: (p) => setProjects((prev) => [p, ...prev]) }))] }));
}
