import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

// ── Analysis step pills ─────────────────────────────────────────────────────

const ANALYSIS_STEPS = [
  { id: "loading",      label: "/loading",      order: 0, delay: 0 },
  { id: "extract",      label: "/extract",      order: 1, delay: 0 },
  { id: "intelligence", label: "/intelligence", order: 2, delay: 0 },
  { id: "economics",    label: "/economics",    order: 3, delay: 0 },
  { id: "writing",      label: "/writing",      order: 4, delay: 0 },
  { id: "report",       label: "/report",       order: 5, delay: 0 },
] as const;

const BACKEND_STEP_ORDER: Record<string, number> = {
  "queued":                          -1,
  "Loading documents":                0,
  "Extracting project facts":         1,
  "Gathering market intelligence":    2,
  "Extracting economic data":         3,
  "Running economics model":          3,
  "Writing report sections":          4,
  "Writing analyst narrative":        4,
  "Finalising report":                5,
  "Complete":                         6,
};

function getStepState(
  step: typeof ANALYSIS_STEPS[number],
  currentStep: string,
  runStatus: string,
): "pending" | "active" | "done" {
  if (runStatus === "complete") return "done";
  if (runStatus === "failed") return "pending";
  const current = BACKEND_STEP_ORDER[currentStep] ?? -1;
  if (current > step.order) return "done";
  if (current === step.order) return "active";
  return "pending";
}

function AnalysisPills({ run }: { run: { step?: string; status: string } }) {
  const step = run.step ?? "queued";
  return (
    <div className="step-pills">
      {ANALYSIS_STEPS.map((s) => {
        const state = getStepState(s, step, run.status);
        return (
          <div key={s.id} className={`step-pill step-pill-${state}`}>
            <span className="step-pill-label">{s.label}</span>
            <div
              className="step-pill-fill"
              style={state === "active" ? { animationDelay: `${s.delay}s` } : undefined}
            >
              <span>{s.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
import {
  archiveProject,
  createComparable,
  createNote,
  createResource,
  createRoyalty,
  deleteComparable,
  deleteFile,
  deleteNote,
  deleteResource,
  deleteRoyalty,
  deleteRun,
  getProject,
  getDrillholes,
  uploadDrillholeFile,
  deleteDrillholes,
  edgarSearchCompanies,
  edgarListFilings,
  edgarListDocuments,
  importFilingDocument,
  getSedarSearchLink,
  getProjectJurisdictionRisk,
  getProjectNews,
  getRun,
  streamRunStatus,
  getResourceSummary,
  getRoyaltySummary,
  ingestUrl,
  listComparables,
  listFiles,
  listNotes,
  listResources,
  listRoyalties,
  listRuns,
  refreshNpv,
  refreshProjectNews,
  renameProject,
  patchProject,
  runSanityCheck,
  startAnalysis,
  updateNote,
  uploadFiles,
  type SanityResult,
} from "../api/client";
import DropZone from "../components/shared/DropZone";
import { useToast } from "../components/shared/Toast";
import type { DrillholeDataset, TracePoint, EdgarCompany, EdgarFiling, EdgarDocument, JurisdictionRisk } from "../api/client";
import type { Comparable, FileRecord, NewsFeed, NewsItem, Note, NpvRefreshResult, Project, ResourceRow, ResourceSummary, Royalty, RoyaltySummary, RunStatus } from "../types";

// ── Icons ──────────────────────────────────────────────────────────────────

function FileIcon() {
  return (
    <svg className="file-icon" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <circle cx="4" cy="10" r="1.5" />
      <circle cx="10" cy="10" r="1.5" />
      <circle cx="16" cy="10" r="1.5" />
    </svg>
  );
}

// ── Project Settings Dropdown ───────────────────────────────────────────────

function ProjectMenu({ onRename, onArchive }: { onRename: () => void; onArchive: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="btn btn-secondary btn-sm"
        onClick={() => setOpen((o) => !o)}
        title="Project settings"
      >
        <DotsIcon />
      </button>
      {open && (
        <div className="project-menu-dropdown">
          <button className="project-menu-item" onClick={() => { setOpen(false); onRename(); }}>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-8.793 8.793-3.536.707.707-3.535 8.794-8.793z" />
            </svg>
            Rename
          </button>
          <button className="project-menu-item" style={{ opacity: 0.5, cursor: "not-allowed" }} disabled>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
            </svg>
            Share <span style={{ fontSize: 10, marginLeft: 4, color: "var(--text-tertiary)" }}>soon</span>
          </button>
          <div className="project-menu-divider" />
          <button className="project-menu-item project-menu-item-danger" onClick={() => { setOpen(false); onArchive(); }}>
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4zM3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
            </svg>
            Archive Project
          </button>
        </div>
      )}
    </div>
  );
}

// ── Rename Modal ────────────────────────────────────────────────────────────

function RenameModal({ current, onClose, onRename }: {
  current: string;
  onClose: () => void;
  onRename: (name: string) => void;
}) {
  const [name, setName] = useState(current);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || name.trim() === current) { onClose(); return; }
    setLoading(true);
    onRename(name.trim());
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-title">Rename Project</div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Project Name</label>
            <input
              className="form-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? <span className="spinner" /> : null} Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

function RunBadge({ status }: { status: RunStatus["status"] }) {
  const label: Record<string, string> = {
    pending: "Queued",
    running: "Running",
    complete: "Complete",
    failed: "Failed",
  };
  const cls: Record<string, string> = {
    pending: "badge-pending",
    running: "badge-running",
    complete: "badge-complete",
    failed: "badge-error",
  };
  return <span className={`badge ${cls[status] ?? "badge-pending"}`}>{label[status] ?? status}</span>;
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [runs, setRuns] = useState<RunStatus[]>([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  // EDGAR / SEDAR import panel
  const [filingPanelOpen, setFilingPanelOpen] = useState(false);
  const [filingTab, setFilingTab] = useState<"edgar" | "sedar">("edgar");
  const [edgarQuery, setEdgarQuery] = useState("");
  const [edgarSearching, setEdgarSearching] = useState(false);
  const [edgarCompanies, setEdgarCompanies] = useState<EdgarCompany[]>([]);
  const [edgarSelectedCompany, setEdgarSelectedCompany] = useState<EdgarCompany | null>(null);
  const [edgarFilings, setEdgarFilings] = useState<EdgarFiling[]>([]);
  const [edgarFilingsLoading, setEdgarFilingsLoading] = useState(false);
  const [edgarSelectedFiling, setEdgarSelectedFiling] = useState<EdgarFiling | null>(null);
  const [edgarDocuments, setEdgarDocuments] = useState<EdgarDocument[]>([]);
  const [edgarDocsLoading, setEdgarDocsLoading] = useState(false);
  const [filingImporting, setFilingImporting] = useState<string | null>(null); // doc url being imported
  const [filingImportMsg, setFilingImportMsg] = useState<string | null>(null);
  const [sedarUrl, setSedarUrl] = useState("");
  const [sedarImporting, setSedarImporting] = useState(false);
  // Drill holes
  const [dhDataset, setDhDataset] = useState<DrillholeDataset | null>(null);
  const [dhLoading, setDhLoading] = useState(false);
  const [dhUploading, setDhUploading] = useState(false);
  const [dhSelectedHole, setDhSelectedHole] = useState<string | null>(null);
  const [dhAnalyte, setDhAnalyte] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"files" | "details" | "notes">("files");
  const [ticker, setTicker] = useState<string>("");
  const [sanity, setSanity] = useState<SanityResult | null>(null);
  const [sanityLoading, setSanityLoading] = useState(false);
  const [jurisdictionRisk, setJurisdictionRisk] = useState<JurisdictionRisk | null>(null);
  const [newsFeed, setNewsFeed] = useState<NewsFeed | null>(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsRefreshing, setNewsRefreshing] = useState(false);
  const [npvRefresh, setNpvRefresh] = useState<NpvRefreshResult | null>(null);
  const [npvRefreshing, setNpvRefreshing] = useState(false);
  const [expandedNewsIds, setExpandedNewsIds] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteText, setNoteText] = useState("");
  const [noteTag, setNoteTag] = useState("");
  const [noteLoading, setNoteLoading] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");
  const [comps, setComps] = useState<Comparable[]>([]);
  const [showCompForm, setShowCompForm] = useState(false);
  const [compLoading, setCompLoading] = useState(false);
  const [compForm, setCompForm] = useState<Partial<Comparable>>({});
  const [resources, setResources] = useState<ResourceRow[]>([]);
  const [resourceSummary, setResourceSummary] = useState<ResourceSummary | null>(null);
  const [showResForm, setShowResForm] = useState(false);
  const [resLoading, setResLoading] = useState(false);
  const [resForm, setResForm] = useState<Partial<ResourceRow>>({ classification: "Measured" });
  const [royaltyList, setRoyaltyList] = useState<Royalty[]>([]);
  const [royaltySummary, setRoyaltySummary] = useState<RoyaltySummary | null>(null);
  const [showRoyaltyForm, setShowRoyaltyForm] = useState(false);
  const [royaltyLoading, setRoyaltyLoading] = useState(false);
  const [royaltyForm, setRoyaltyForm] = useState<Partial<Royalty>>({ royalty_type: "NSR", buyback_option: false });
  const [showRename, setShowRename] = useState(false);
  const stopStreamRef = useRef<(() => void) | null>(null);

  const id = projectId!;

  useEffect(() => {
    Promise.all([
      getProject(id),
      listFiles(id),
      listRuns(id),
      listNotes(id),
      listComparables(id),
      listResources(id),
      getResourceSummary(id),
      listRoyalties(id),
      getRoyaltySummary(id),
    ]).then(([p, f, r, n, c, res, resSummary, roy, roySummary]) => {
      setProject(p);
      setTicker(p.ticker ?? "");
      setFiles(f);
      setRuns(r);
      setNotes(n);
      setComps(c);
      setResources(res);
      setResourceSummary(resSummary);
      setRoyaltyList(roy);
      setRoyaltySummary(roySummary);
    }).catch(() => {
      toast("Could not load project", "error");
    });
    return () => { stopStreamRef.current?.(); };
  }, [id]);

  // Stream live run status updates via SSE (replaces polling)
  function startStreaming(runId: string) {
    stopStreamRef.current?.();
    stopStreamRef.current = null;

    function handleUpdate(updated: RunStatus) {
      setRuns((prev) => prev.map((r) => r.run_id === runId ? updated : r));
      if (updated.status === "complete" || updated.status === "failed") {
        stopStreamRef.current?.();
        stopStreamRef.current = null;
        setAnalyzing(false);
        if (updated.status === "complete") {
          toast("Analysis complete! View your report.", "success");
          setActiveTab("details");
          Promise.all([
            listResources(id),
            getResourceSummary(id),
            listRoyalties(id),
            getRoyaltySummary(id),
            listComparables(id),
          ]).then(([res, resSummary, roy, roySummary, comps]) => {
            setResources(res);
            setResourceSummary(resSummary);
            setRoyaltyList(roy);
            setRoyaltySummary(roySummary);
            setComps(comps);
          }).catch(() => {/* non-fatal */});
          runSanityCheck(id).then(setSanity).catch(() => {/* non-fatal */});
        } else {
          toast(`Analysis failed: ${updated.error ?? "Unknown error"}`, "error");
        }
      }
    }

    streamRunStatus(id, runId, handleUpdate, () => {
      // SSE connection dropped — fall back to a single fetch to get final state
      getRun(id, runId).then(handleUpdate).catch(() => setAnalyzing(false));
    }).then((stop) => {
      stopStreamRef.current = stop;
    });
  }

  async function handleUpload(newFiles: File[]) {
    setUploading(true);
    try {
      const result = await uploadFiles(id, newFiles);
      toast(`${result.queued.length} file(s) uploaded`, "success");
      if (result.skipped.length) toast(`${result.skipped.length} file(s) skipped (unsupported type)`, "info");
      const updated = await listFiles(id);
      setFiles(updated);
    } catch (err: unknown) {
      toast((err as Error).message ?? "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleUrlIngest(e: React.FormEvent) {
    e.preventDefault();
    const url = urlInput.trim();
    if (!url) return;
    setUrlLoading(true);
    try {
      const result = await ingestUrl(id, url);
      toast(`Imported "${result.filename}" from URL`, "success");
      setUrlInput("");
      const updated = await listFiles(id);
      setFiles(updated);
    } catch (err: unknown) {
      toast((err as Error).message ?? "Failed to import URL", "error");
    } finally {
      setUrlLoading(false);
    }
  }

  // ── EDGAR / SEDAR handlers ────────────────────────────────────────────────

  async function handleEdgarSearch() {
    if (!edgarQuery.trim()) return;
    setEdgarSearching(true);
    setEdgarCompanies([]);
    setEdgarSelectedCompany(null);
    setEdgarFilings([]);
    try {
      const res = await edgarSearchCompanies(edgarQuery.trim());
      setEdgarCompanies(res.results);
      if (res.results.length === 0) toast("No companies found on EDGAR for that query", "error");
    } catch {
      toast("EDGAR search failed — check your connection", "error");
    } finally {
      setEdgarSearching(false);
    }
  }

  async function handleEdgarSelectCompany(company: EdgarCompany) {
    setEdgarSelectedCompany(company);
    setEdgarFilings([]);
    setEdgarSelectedFiling(null);
    setEdgarDocuments([]);
    setFilingImportMsg(null);
    // Auto-save ticker from the selected company
    if (company.ticker) {
      setTicker(company.ticker);
      handleSaveTicker(company.ticker);
    }
    setEdgarFilingsLoading(true);
    try {
      const res = await edgarListFilings(company.cik);
      setEdgarFilings(res.filings);
    } catch {
      toast("Failed to load EDGAR filings", "error");
    } finally {
      setEdgarFilingsLoading(false);
    }
  }

  async function handleEdgarSelectFiling(filing: EdgarFiling) {
    setEdgarSelectedFiling(filing);
    setEdgarDocuments([]);
    setFilingImportMsg(null);
    setEdgarDocsLoading(true);
    try {
      const res = await edgarListDocuments(filing.cik, filing.accession_number);
      setEdgarDocuments(res.documents);
    } catch {
      toast("Failed to load filing documents", "error");
    } finally {
      setEdgarDocsLoading(false);
    }
  }

  async function handleImportEdgarDoc(doc: EdgarDocument) {
    setFilingImporting(doc.url);
    setFilingImportMsg(null);
    try {
      const res = await importFilingDocument(id, doc.url, doc.filename, "edgar");
      setFilingImportMsg(`✓ Imported "${res.filename}" (${Math.round(res.size_bytes / 1024)}KB)`);
      const updated = await listFiles(id);
      setFiles(updated);
    } catch (err: unknown) {
      setFilingImportMsg(`Failed: ${(err as Error).message ?? "Unknown error"}`);
    } finally {
      setFilingImporting(null);
    }
  }

  async function handleImportSedar() {
    const url = sedarUrl.trim();
    if (!url) return;
    setSedarImporting(true);
    setFilingImportMsg(null);
    try {
      const res = await importFilingDocument(id, url, undefined, "sedar");
      setFilingImportMsg(`✓ Imported "${res.filename}" (${Math.round(res.size_bytes / 1024)}KB)`);
      setSedarUrl("");
      const updated = await listFiles(id);
      setFiles(updated);
    } catch (err: unknown) {
      setFilingImportMsg(`Failed: ${(err as Error).message ?? "Unknown error"}`);
    } finally {
      setSedarImporting(false);
    }
  }

  // ── Drill hole handlers ───────────────────────────────────────────────────

  async function handleDhUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setDhUploading(true);
    try {
      const result = await uploadDrillholeFile(id, file);
      toast(`Imported ${result.table_type}: ${result.row_count} rows, ${result.hole_count} holes`, "success");
      const updated = await getDrillholes(id);
      setDhDataset(updated);
      if (!dhAnalyte && updated.analytes.length) setDhAnalyte(updated.analytes[0]);
    } catch (err: unknown) {
      toast((err as Error).message ?? "Upload failed", "error");
    } finally {
      setDhUploading(false);
      e.target.value = "";
    }
  }

  async function handleDhClear() {
    if (!confirm("Delete all drill hole data for this project?")) return;
    try {
      await deleteDrillholes(id);
      setDhDataset(null);
      setDhSelectedHole(null);
      toast("Drill hole data cleared", "success");
    } catch {
      toast("Failed to clear drill hole data", "error");
    }
  }

  async function handleDeleteFile(filename: string) {
    try {
      await deleteFile(id, filename);
      setFiles((prev) => prev.filter((f) => f.filename !== filename));
      toast(`Removed ${filename}`, "info");
    } catch {
      toast("Failed to remove file", "error");
    }
  }

  async function handleDeleteRun(runId: string) {
    try {
      await deleteRun(id, runId);
      setRuns((prev) => prev.filter((r) => r.run_id !== runId));
      toast("Run deleted", "info");
    } catch {
      toast("Failed to delete run", "error");
    }
  }

  async function handleRename(name: string) {
    try {
      await renameProject(id, name);
      setProject((p) => p ? { ...p, name } : p);
      toast(`Renamed to "${name}"`, "success");
    } catch {
      toast("Failed to rename project", "error");
    } finally {
      setShowRename(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!noteText.trim()) return;
    setNoteLoading(true);
    try {
      const note = await createNote(id, noteText.trim(), noteTag.trim() || undefined);
      setNotes((prev) => [note, ...prev]);
      setNoteText("");
      setNoteTag("");
      toast("Note saved", "success");
    } catch {
      toast("Failed to save note", "error");
    } finally {
      setNoteLoading(false);
    }
  }

  async function handleSaveEdit(noteId: string) {
    if (!editingText.trim()) return;
    try {
      const updated = await updateNote(id, noteId, editingText.trim());
      setNotes((prev) => prev.map((n) => n.note_id === noteId ? updated : n));
      setEditingNoteId(null);
      setEditingText("");
    } catch {
      toast("Failed to update note", "error");
    }
  }

  async function handleDeleteNote(noteId: string) {
    try {
      await deleteNote(id, noteId);
      setNotes((prev) => prev.filter((n) => n.note_id !== noteId));
      toast("Note deleted", "info");
    } catch {
      toast("Failed to delete note", "error");
    }
  }

  async function handleAddResource(e: React.FormEvent) {
    e.preventDefault();
    if (!resForm.classification) return;
    setResLoading(true);
    try {
      const row = await createResource(id, {
        classification: resForm.classification as ResourceRow["classification"],
        domain: resForm.domain ?? null,
        tonnage_mt: resForm.tonnage_mt ?? null,
        grade_value: resForm.grade_value ?? null,
        grade_unit: resForm.grade_unit ?? null,
        contained_metal: resForm.contained_metal ?? null,
        metal_unit: resForm.metal_unit ?? null,
        cut_off_grade: resForm.cut_off_grade ?? null,
        notes: resForm.notes ?? null,
      });
      const [newRows, newSummary] = await Promise.all([listResources(id), getResourceSummary(id)]);
      setResources(newRows);
      setResourceSummary(newSummary);
      setResForm({ classification: "Measured" });
      setShowResForm(false);
      toast("Resource row added", "success");
    } catch {
      toast("Failed to add resource row", "error");
    } finally {
      setResLoading(false);
    }
  }

  async function handleDeleteResource(rowId: string) {
    try {
      await deleteResource(id, rowId);
      const [newRows, newSummary] = await Promise.all([listResources(id), getResourceSummary(id)]);
      setResources(newRows);
      setResourceSummary(newSummary);
      toast("Row removed", "info");
    } catch {
      toast("Failed to remove row", "error");
    }
  }

  async function handleRunSanityCheck() {
    setSanityLoading(true);
    try {
      const result = await runSanityCheck(id);
      setSanity(result);
    } catch {
      toast("Sanity check failed", "error");
    } finally {
      setSanityLoading(false);
    }
  }

  async function handleAddRoyalty(e: React.FormEvent) {
    e.preventDefault();
    if (!royaltyForm.holder?.trim()) return;
    setRoyaltyLoading(true);
    try {
      await createRoyalty(id, {
        royalty_type: (royaltyForm.royalty_type ?? "NSR") as Royalty["royalty_type"],
        holder: royaltyForm.holder ?? "",
        rate_pct: royaltyForm.rate_pct ?? null,
        metals_covered: royaltyForm.metals_covered ?? null,
        area_covered: royaltyForm.area_covered ?? null,
        stream_pct: royaltyForm.stream_pct ?? null,
        stream_purchase_price: royaltyForm.stream_purchase_price ?? null,
        stream_purchase_unit: royaltyForm.stream_purchase_unit ?? null,
        sliding_scale_notes: royaltyForm.sliding_scale_notes ?? null,
        production_rate: royaltyForm.production_rate ?? null,
        production_unit: royaltyForm.production_unit ?? null,
        buyback_option: royaltyForm.buyback_option ?? false,
        buyback_price_musd: royaltyForm.buyback_price_musd ?? null,
        recorded_instrument: royaltyForm.recorded_instrument ?? null,
        notes: royaltyForm.notes ?? null,
      });
      const [newList, newSummary] = await Promise.all([listRoyalties(id), getRoyaltySummary(id)]);
      setRoyaltyList(newList);
      setRoyaltySummary(newSummary);
      setRoyaltyForm({ royalty_type: "NSR", buyback_option: false });
      setShowRoyaltyForm(false);
      toast("Royalty / stream added", "success");
    } catch {
      toast("Failed to add royalty", "error");
    } finally {
      setRoyaltyLoading(false);
    }
  }

  async function handleDeleteRoyalty(royaltyId: string) {
    try {
      await deleteRoyalty(id, royaltyId);
      const [newList, newSummary] = await Promise.all([listRoyalties(id), getRoyaltySummary(id)]);
      setRoyaltyList(newList);
      setRoyaltySummary(newSummary);
      toast("Removed", "info");
    } catch {
      toast("Failed to remove royalty", "error");
    }
  }

  async function handleAddComp(e: React.FormEvent) {
    e.preventDefault();
    if (!compForm.project_name?.trim()) return;
    setCompLoading(true);
    try {
      const comp = await createComparable(id, {
        project_name: compForm.project_name ?? "",
        acquirer: compForm.acquirer ?? null,
        seller: compForm.seller ?? null,
        commodity: compForm.commodity ?? null,
        transaction_date: compForm.transaction_date ?? null,
        transaction_value_musd: compForm.transaction_value_musd ?? null,
        resource_moz_or_mlb: compForm.resource_moz_or_mlb ?? null,
        price_per_unit_usd: compForm.price_per_unit_usd ?? null,
        study_stage: compForm.study_stage ?? null,
        jurisdiction: compForm.jurisdiction ?? null,
        notes: compForm.notes ?? null,
      });
      setComps((prev) => [comp, ...prev]);
      setCompForm({});
      setShowCompForm(false);
      toast("Comparable added", "success");
    } catch {
      toast("Failed to add comparable", "error");
    } finally {
      setCompLoading(false);
    }
  }

  async function handleDeleteComp(compId: string) {
    try {
      await deleteComparable(id, compId);
      setComps((prev) => prev.filter((c) => c.comp_id !== compId));
      toast("Comparable removed", "info");
    } catch {
      toast("Failed to remove comparable", "error");
    }
  }

  async function handleArchive() {
    if (!window.confirm(`Archive "${project?.name}"? It will be moved to the _archive folder and hidden from your projects list.`)) return;
    try {
      await archiveProject(id);
      toast(`"${project?.name}" archived`, "info");
      navigate("/projects");
    } catch {
      toast("Failed to archive project", "error");
    }
  }

  async function handleSaveTicker(value: string) {
    const t = value.toUpperCase().trim().slice(0, 12);
    setTicker(t);
    try {
      const updated = await patchProject(id, { ticker: t || null });
      setProject(updated);
    } catch {
      // non-critical, ignore
    }
  }

  async function handleNpvRefresh() {
    setNpvRefreshing(true);
    try {
      const result = await refreshNpv(id);
      setNpvRefresh(result);
    } catch (err: unknown) {
      toast((err as Error).message ?? "NPV refresh failed", "error");
    } finally {
      setNpvRefreshing(false);
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
      setActiveTab("details");
      startStreaming(run.run_id);
      toast("Analysis started — this may take 1–3 minutes", "info");
    } catch (err: unknown) {
      toast((err as Error).message ?? "Failed to start analysis", "error");
      setAnalyzing(false);
    }
  }

  if (!project) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <span className="spinner" style={{ width: 28, height: 28, color: "var(--text-tertiary)" }} />
      </div>
    );
  }

  const activeRun = runs.find((r) => r.status === "running" || r.status === "pending");
  const completeRuns = runs.filter((r) => r.status === "complete");

  return (
    <>
      {/* Header */}
      <div className="project-header">
        <div className="project-header-left">
          <div className="project-title-row">
            <h1 className="project-title">{project.name}</h1>
            <span className="badge badge-empty">{project.study_type}</span>
          </div>
          <div className="project-meta-row">
            {project.commodity && <span className="project-meta-chip">{project.commodity}</span>}
            <span className="project-meta-chip" style={{ color: "var(--text-tertiary)" }}>
              {files.length} files · {runs.length} runs
            </span>
          </div>
        </div>
        <div className="project-header-right">
          <ProjectMenu onRename={() => setShowRename(true)} onArchive={handleArchive} />
          {runs.some((r) => r.status === "complete") && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleNpvRefresh}
              disabled={npvRefreshing}
              title="Re-estimate NPV at today's commodity prices"
            >
              {npvRefreshing ? <span className="spinner" style={{ width: 13, height: 13 }} /> : "↻"} Refresh NPV
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleRunAnalysis}
            disabled={analyzing || files.length === 0}
          >
            {analyzing ? (
              <><span className="spinner" /> Analyzing…</>
            ) : (
              <><PlayIcon /> Run Analysis</>
            )}
          </button>
        </div>
      </div>

      {/* NPV delta card */}
      {npvRefresh && (
        <div className={`npv-delta-card npv-delta-${
          npvRefresh.npv_delta_pct == null ? "neutral"
            : npvRefresh.npv_delta_pct > 2 ? "up"
            : npvRefresh.npv_delta_pct < -2 ? "down"
            : "neutral"
        }`}>
          <div className="npv-delta-inner">
            <div className="npv-delta-main">
              <span className="npv-delta-label">NPV at today's prices</span>
              <span className="npv-delta-value">
                {npvRefresh.new_npv_musd != null
                  ? `$${npvRefresh.new_npv_musd.toLocaleString()}M`
                  : npvRefresh.last_npv_musd != null
                    ? `$${npvRefresh.last_npv_musd.toLocaleString()}M (unchanged)`
                    : "—"
                }
              </span>
              {npvRefresh.npv_delta_pct != null && (
                <span className={`npv-delta-pct ${npvRefresh.npv_delta_pct >= 0 ? "npv-delta-pct--up" : "npv-delta-pct--down"}`}>
                  {npvRefresh.npv_delta_pct >= 0 ? "▲" : "▼"} {Math.abs(npvRefresh.npv_delta_pct).toFixed(1)}% since last run
                </span>
              )}
            </div>
            {(npvRefresh.commodity || npvRefresh.current_price != null) && (
              <div className="npv-delta-prices">
                {npvRefresh.current_price != null && (
                  <span className="npv-delta-price-chip">
                    {npvRefresh.commodity ?? "commodity"} {npvRefresh.current_price.toLocaleString()}
                    {npvRefresh.price_change_pct != null && (
                      <span style={{ color: npvRefresh.price_change_pct >= 0 ? "var(--success)" : "#ef4444" }}>
                        {" "}({npvRefresh.price_change_pct >= 0 ? "+" : ""}{npvRefresh.price_change_pct.toFixed(1)}%)
                      </span>
                    )}
                  </span>
                )}
              </div>
            )}
            {npvRefresh.error && (
              <div className="npv-delta-error">{npvRefresh.error}</div>
            )}
          </div>
          <button className="npv-delta-dismiss" onClick={() => setNpvRefresh(null)} title="Dismiss">×</button>
        </div>
      )}

      {showRename && (
        <RenameModal
          current={project.name}
          onClose={() => setShowRename(false)}
          onRename={handleRename}
        />
      )}

      {/* Analysis progress pills */}
      {activeRun && (
        <div style={{ marginBottom: 24 }}>
          <div className="run-panel">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Analysis in progress</span>
              <RunBadge status={activeRun.status} />
            </div>
            <AnalysisPills run={activeRun} />
          </div>
        </div>
      )}

      {/* Completed runs quick link */}
      {completeRuns.length > 0 && (
        <div className="card" style={{ marginBottom: 24, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 600 }}>{completeRuns.length} report{completeRuns.length > 1 ? "s" : ""} ready</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 3 }}>
              View the latest results or compare two runs side by side
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {completeRuns.length >= 2 && (
              <Link to={`/projects/${id}/compare`} className="btn btn-secondary">
                Compare
              </Link>
            )}
            <Link
              to={`/projects/${id}/report/${completeRuns[0].run_id}`}
              className="btn btn-primary"
            >
              View Report
            </Link>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab ${activeTab === "files" ? "active" : ""}`} onClick={() => setActiveTab("files")}>
          Files {files.length > 0 ? `(${files.length})` : ""}
        </button>
        <button
          className={`tab ${activeTab === "details" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("details");
            if (!sanity) handleRunSanityCheck();
            if (!jurisdictionRisk) getProjectJurisdictionRisk(id).then(r => setJurisdictionRisk(r)).catch(() => {});
            if (!newsFeed && !newsLoading) {
              setNewsLoading(true);
              getProjectNews(id).then(setNewsFeed).catch(() => {}).finally(() => setNewsLoading(false));
            }
            if (!dhDataset && !dhLoading) {
              setDhLoading(true);
              getDrillholes(id).then(d => { setDhDataset(d); if (d.analytes.length) setDhAnalyte(d.analytes[0]); }).catch(() => {}).finally(() => setDhLoading(false));
            }
          }}
        >
          Details
        </button>
        <button className={`tab ${activeTab === "notes" ? "active" : ""}`} onClick={() => setActiveTab("notes")}>
          Notes {notes.length > 0 ? `(${notes.length})` : ""}
        </button>
      </div>

      {/* Files tab */}
      {activeTab === "files" && (
        <>
          <DropZone onFiles={handleUpload} disabled={uploading} />

          {/* URL import row */}
          <form onSubmit={handleUrlIngest} style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <span style={{
                position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)",
                color: "var(--text-tertiary)", pointerEvents: "none", display: "flex",
              }}>
                <svg width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </span>
              <input
                className="form-input"
                type="url"
                placeholder="Import from URL — paste a press release, article or filing…"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                disabled={urlLoading}
                style={{ paddingLeft: 32, fontSize: 13 }}
              />
            </div>
            <button
              type="submit"
              className="btn btn-secondary btn-sm"
              disabled={urlLoading || !urlInput.trim()}
              style={{ whiteSpace: "nowrap" }}
            >
              {urlLoading ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Fetching…</> : "Import"}
            </button>
          </form>

          {/* EDGAR / SEDAR import panel */}
          <div style={{ marginTop: 8 }}>
            <button
              type="button"
              onClick={() => setFilingPanelOpen(v => !v)}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "none", border: "none", cursor: "pointer",
                fontSize: 12, color: "var(--text-tertiary)", padding: "4px 0",
              }}
            >
              <span style={{ fontSize: 15, transform: filingPanelOpen ? "rotate(90deg)" : "none", display: "inline-block", transition: "transform 0.15s" }}>▶</span>
              Import from EDGAR or SEDAR+
            </button>

            {filingPanelOpen && (
              <div style={{
                marginTop: 8, border: "1px solid var(--border)", borderRadius: 8,
                background: "var(--bg-secondary)", overflow: "hidden",
              }}>
                {/* Tab bar */}
                <div style={{ display: "flex", borderBottom: "1px solid var(--border)" }}>
                  {(["edgar", "sedar"] as const).map(t => (
                    <button key={t} onClick={() => setFilingTab(t)} style={{
                      flex: 1, padding: "8px 0", fontSize: 12, fontWeight: 600,
                      background: filingTab === t ? "var(--bg-primary)" : "none",
                      border: "none", cursor: "pointer",
                      borderBottom: filingTab === t ? "2px solid var(--color-accent)" : "2px solid transparent",
                      color: filingTab === t ? "var(--text-primary)" : "var(--text-tertiary)",
                    }}>
                      {t === "edgar" ? "SEC EDGAR" : "SEDAR+"}
                    </button>
                  ))}
                </div>

                <div style={{ padding: "14px 16px" }}>
                  {filingTab === "edgar" && (
                    <>
                      {/* Step 1: Search company */}
                      {!edgarSelectedCompany && (
                        <>
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
                            Search for a company on SEC EDGAR to browse their filings (40-F, 10-K, 20-F, 6-K).
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <input
                              className="form-input"
                              style={{ flex: 1, fontSize: 13 }}
                              placeholder="Company name or ticker (e.g. Barrick, GOLD)"
                              value={edgarQuery}
                              onChange={e => setEdgarQuery(e.target.value)}
                              onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleEdgarSearch(); } }}
                            />
                            <button className="btn btn-secondary btn-sm" disabled={edgarSearching || !edgarQuery.trim()} onClick={handleEdgarSearch}>
                              {edgarSearching ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Searching…</> : "Search"}
                            </button>
                          </div>
                          {edgarCompanies.length > 0 && (
                            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
                              {edgarCompanies.map(c => (
                                <button key={c.cik} onClick={() => handleEdgarSelectCompany(c)} style={{
                                  display: "flex", alignItems: "center", gap: 10,
                                  padding: "7px 10px", background: "var(--bg-primary)",
                                  border: "1px solid var(--border)", borderRadius: 6,
                                  cursor: "pointer", textAlign: "left",
                                }}>
                                  <span style={{ fontWeight: 600, fontSize: 13, flex: 1 }}>{c.name}</span>
                                  {c.ticker && <span style={{ fontSize: 11, color: "var(--text-tertiary)", fontFamily: "monospace" }}>{c.ticker}</span>}
                                  {c.exchange && <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{c.exchange}</span>}
                                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>CIK {c.cik}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </>
                      )}

                      {/* Step 2: Browse filings */}
                      {edgarSelectedCompany && !edgarSelectedFiling && (
                        <>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                            <div>
                              <span style={{ fontWeight: 700, fontSize: 13 }}>{edgarSelectedCompany.name}</span>
                              {edgarSelectedCompany.ticker && <span style={{ fontSize: 11, color: "var(--text-tertiary)", marginLeft: 8 }}>{edgarSelectedCompany.ticker}</span>}
                            </div>
                            <button className="btn btn-secondary btn-sm" onClick={() => { setEdgarSelectedCompany(null); setEdgarFilings([]); setEdgarCompanies([]); }}>
                              ← Back
                            </button>
                          </div>
                          {edgarFilingsLoading && <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}><span className="spinner" style={{ width: 12, height: 12 }} /> Loading filings…</div>}
                          {!edgarFilingsLoading && edgarFilings.length === 0 && (
                            <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}>No 40-F / 10-K / 20-F / 6-K filings found.</div>
                          )}
                          {edgarFilings.map(f => (
                            <button key={f.accession_number} onClick={() => handleEdgarSelectFiling(f)} style={{
                              display: "flex", alignItems: "center", gap: 10, width: "100%",
                              padding: "7px 10px", marginBottom: 4, background: "var(--bg-primary)",
                              border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer", textAlign: "left",
                            }}>
                              <span style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 7px", fontSize: 11, fontWeight: 700, fontFamily: "monospace", whiteSpace: "nowrap" }}>
                                {f.form_type}
                              </span>
                              <span style={{ flex: 1, fontSize: 13 }}>{f.primary_doc_description || f.primary_document || "Filing"}</span>
                              <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{f.filing_date}</span>
                            </button>
                          ))}
                        </>
                      )}

                      {/* Step 3: Browse documents in filing */}
                      {edgarSelectedFiling && (
                        <>
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                            <div style={{ fontSize: 13 }}>
                              <span style={{ fontWeight: 600 }}>{edgarSelectedCompany?.name}</span>
                              <span style={{ color: "var(--text-tertiary)", marginLeft: 8 }}>{edgarSelectedFiling.form_type} · {edgarSelectedFiling.filing_date}</span>
                            </div>
                            <button className="btn btn-secondary btn-sm" onClick={() => { setEdgarSelectedFiling(null); setEdgarDocuments([]); }}>
                              ← Back
                            </button>
                          </div>
                          {edgarDocsLoading && <div style={{ fontSize: 13, color: "var(--text-tertiary)" }}><span className="spinner" style={{ width: 12, height: 12 }} /> Loading documents…</div>}
                          {filingImportMsg && (
                            <div style={{ fontSize: 12, padding: "6px 10px", marginBottom: 8, borderRadius: 5, background: filingImportMsg.startsWith("✓") ? "#dcfce7" : "#fee2e2", color: filingImportMsg.startsWith("✓") ? "#166534" : "#991b1b" }}>
                              {filingImportMsg}
                            </div>
                          )}
                          {edgarDocuments.map(doc => (
                            <div key={doc.url} style={{
                              display: "flex", alignItems: "center", gap: 10,
                              padding: "7px 10px", marginBottom: 4, background: "var(--bg-primary)",
                              border: "1px solid var(--border)", borderRadius: 6,
                            }}>
                              <span style={{ fontFamily: "monospace", fontSize: 11, color: "var(--text-tertiary)", minWidth: 36 }}>{doc.document_type}</span>
                              <span style={{ flex: 1, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                {doc.description || doc.filename}
                              </span>
                              {doc.size_bytes > 0 && <span style={{ fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{Math.round(doc.size_bytes / 1024)}KB</span>}
                              <button
                                className="btn btn-secondary btn-sm"
                                disabled={filingImporting === doc.url}
                                onClick={() => handleImportEdgarDoc(doc)}
                                style={{ whiteSpace: "nowrap", flexShrink: 0 }}
                              >
                                {filingImporting === doc.url
                                  ? <><span className="spinner" style={{ width: 11, height: 11 }} /> Importing…</>
                                  : "Import"}
                              </button>
                            </div>
                          ))}
                        </>
                      )}
                    </>
                  )}

                  {filingTab === "sedar" && (
                    <>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.6 }}>
                        SEDAR+ does not provide a public API. Search for a company below to open the SEDAR+ website, then copy the document download URL and paste it here.
                      </div>
                      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                        <input
                          className="form-input"
                          style={{ flex: 1, fontSize: 13 }}
                          placeholder="Company name (e.g. Agnico Eagle)"
                          value={edgarQuery}
                          onChange={e => setEdgarQuery(e.target.value)}
                        />
                        <button className="btn btn-secondary btn-sm" onClick={() => {
                          getSedarSearchLink(edgarQuery).then(r => window.open(r.search_url, "_blank")).catch(() => {
                            window.open(`https://www.sedarplus.ca/csa-party/records/search.html?keyword=${encodeURIComponent(edgarQuery)}`, "_blank");
                          });
                        }} disabled={!edgarQuery.trim()}>
                          Open SEDAR+
                        </button>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
                        Paste a SEDAR+ document URL:
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <input
                          className="form-input"
                          style={{ flex: 1, fontSize: 13 }}
                          placeholder="https://www.sedarplus.ca/..."
                          value={sedarUrl}
                          onChange={e => setSedarUrl(e.target.value)}
                        />
                        <button className="btn btn-secondary btn-sm" disabled={sedarImporting || !sedarUrl.trim()} onClick={handleImportSedar}>
                          {sedarImporting ? <><span className="spinner" style={{ width: 11, height: 11 }} /> Importing…</> : "Import"}
                        </button>
                      </div>
                      {filingImportMsg && (
                        <div style={{ fontSize: 12, padding: "6px 10px", marginTop: 8, borderRadius: 5, background: filingImportMsg.startsWith("✓") ? "#dcfce7" : "#fee2e2", color: filingImportMsg.startsWith("✓") ? "#166534" : "#991b1b" }}>
                          {filingImportMsg}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {uploading && (
            <div style={{ textAlign: "center", padding: "16px 0", color: "var(--text-secondary)", fontSize: 13 }}>
              <span className="spinner" style={{ width: 16, height: 16 }} /> Uploading…
            </div>
          )}

          {files.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div className="section-header">
                <div className="section-title">File Library ({files.length})</div>
              </div>
              <div className="file-list">
                {files.map((f) => (
                  <div key={f.filename} className="file-row">
                    <FileIcon />
                    <span className="file-name">{f.filename}</span>
                    <span className="file-size">{formatBytes(f.size_bytes)}</span>
                    <button
                      className="btn-icon-only"
                      onClick={() => handleDeleteFile(f.filename)}
                      title="Remove file"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {files.length === 0 && !uploading && (
            <div style={{ textAlign: "center", padding: "20px", color: "var(--text-secondary)", fontSize: 13 }}>
              No files yet — drop your documents above to get started
            </div>
          )}
        </>
      )}

      {/* Notes tab */}
      {activeTab === "notes" && (
        <>
          {/* Add note form */}
          <form onSubmit={handleAddNote} style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <select
                className="form-input"
                value={noteTag}
                onChange={(e) => setNoteTag(e.target.value)}
                style={{ width: 140, fontSize: 13, flexShrink: 0 }}
              >
                <option value="">No tag</option>
                <option value="red flag">🚩 Red flag</option>
                <option value="follow up">📌 Follow up</option>
                <option value="assumption">⚠️ Assumption</option>
                <option value="positive">✅ Positive</option>
                <option value="observation">💡 Observation</option>
              </select>
              <input
                className="form-input"
                placeholder="Quick note — e.g. 'Capex seems low for this jurisdiction'"
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                disabled={noteLoading}
                style={{ flex: 1, fontSize: 13 }}
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={noteLoading || !noteText.trim()}
                style={{ whiteSpace: "nowrap" }}
              >
                {noteLoading ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "Add Note"}
              </button>
            </div>
          </form>

          {/* Notes list */}
          {notes.length === 0 ? (
            <div className="empty-state">
              <h3>No notes yet</h3>
              <p>Add observations, red flags, or follow-up items above</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {notes.map((note) => (
                <div key={note.note_id} className="card" style={{ padding: "14px 16px" }}>
                  {editingNoteId === note.note_id ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <textarea
                        className="form-input"
                        value={editingText}
                        onChange={(e) => setEditingText(e.target.value)}
                        rows={3}
                        autoFocus
                        style={{ fontSize: 13, resize: "vertical" }}
                      />
                      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => { setEditingNoteId(null); setEditingText(""); }}>
                          Cancel
                        </button>
                        <button className="btn btn-primary btn-sm" onClick={() => handleSaveEdit(note.note_id)}>
                          Save
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <div style={{ flex: 1 }}>
                        {note.tag && (
                          <div style={{
                            display: "inline-block",
                            fontSize: 11,
                            fontWeight: 600,
                            padding: "2px 8px",
                            borderRadius: 4,
                            marginBottom: 6,
                            background: note.tag === "red flag" ? "rgba(220,53,53,0.1)" :
                                        note.tag === "follow up" ? "rgba(99,102,241,0.1)" :
                                        note.tag === "assumption" ? "rgba(245,158,11,0.1)" :
                                        note.tag === "positive" ? "rgba(34,197,94,0.1)" :
                                        "rgba(107,114,128,0.1)",
                            color: note.tag === "red flag" ? "#dc3535" :
                                   note.tag === "follow up" ? "#6366f1" :
                                   note.tag === "assumption" ? "#d97706" :
                                   note.tag === "positive" ? "#16a34a" :
                                   "var(--text-secondary)",
                          }}>
                            {note.tag === "red flag" ? "🚩" : note.tag === "follow up" ? "📌" : note.tag === "assumption" ? "⚠️" : note.tag === "positive" ? "✅" : "💡"} {note.tag}
                          </div>
                        )}
                        <div style={{ fontSize: 14, lineHeight: 1.55, color: "var(--text-primary)" }}>
                          {note.content}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 6 }}>
                          {new Date(note.created_at).toLocaleString()}
                          {note.updated_at !== note.created_at && " · edited"}
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                        <button
                          className="btn-icon-only"
                          title="Edit note"
                          onClick={() => { setEditingNoteId(note.note_id); setEditingText(note.content); }}
                        >
                          <svg width="13" height="13" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-8.793 8.793-3.536.707.707-3.535 8.794-8.793z" />
                          </svg>
                        </button>
                        <button
                          className="btn-icon-only"
                          title="Delete note"
                          onClick={() => handleDeleteNote(note.note_id)}
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── Details tab — all secondary data as scrollable sub-sections ── */}
      {activeTab === "details" && (
        <div>

          {/* Checks & Jurisdiction */}
          <div className="details-section">
            <div className="details-section-heading">Jurisdiction &amp; Sanity Checks</div>
          {/* Jurisdiction Parameters */}
          {jurisdictionRisk && !jurisdictionRisk.not_found && (
            <div style={{ marginBottom: 28 }}>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
                {jurisdictionRisk.name}
                <span style={{ fontWeight: 400, color: "var(--text-tertiary)", fontSize: 12, marginLeft: 10 }}>
                  {jurisdictionRisk.country} · {jurisdictionRisk.region}
                </span>
              </div>
              <div style={{ overflowX: "auto", marginBottom: 14 }}>
                <table className="details-param-table">
                  <tbody>
                    {[
                      ["Risk Tier", `Tier ${jurisdictionRisk.risk_tier} — ${["","Top Jurisdiction","Favourable","Elevated Risk","Very High Risk"][jurisdictionRisk.risk_tier as number] ?? ""}`],
                      ["Risk Level", String(jurisdictionRisk.risk_level ?? "—").replace(/_/g, " ")],
                      ["Political Stability", String(jurisdictionRisk.political_stability ?? "—").replace(/_/g, " ")],
                      ["Corporate Tax Rate", jurisdictionRisk.corporate_tax_rate_pct != null ? `${jurisdictionRisk.corporate_tax_rate_pct}%` : "n/a"],
                      ["State Royalty Rate", jurisdictionRisk.royalty_rate ?? "n/a"],
                      ["Permitting Timeline", jurisdictionRisk.permitting_timeline_months != null ? `~${jurisdictionRisk.permitting_timeline_months} months` : "n/a"],
                      ...(jurisdictionRisk.fraser_rank_approx != null ? [["Fraser Institute PPI Rank", `~#${jurisdictionRisk.fraser_rank_approx}`]] : []),
                    ].map(([k, v]) => (
                      <tr key={k as string}>
                        <td className="details-param-key">{k as string}</td>
                        <td className="details-param-val">{v as string}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(jurisdictionRisk.key_strengths?.length > 0 || jurisdictionRisk.key_risks?.length > 0) && (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
                  {jurisdictionRisk.key_strengths?.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Strengths</div>
                      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.75 }}>
                        {jurisdictionRisk.key_strengths.slice(0, 5).map((s: string, i: number) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                  {jurisdictionRisk.key_risks?.length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Key Risks</div>
                      <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.75 }}>
                        {jurisdictionRisk.key_risks.slice(0, 5).map((r: string, i: number) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              {jurisdictionRisk.recent_policy_notes && (
                <p style={{ marginTop: 12, fontSize: 12.5, color: "var(--text-secondary)", lineHeight: 1.65, fontStyle: "italic" }}>
                  {jurisdictionRisk.recent_policy_notes}
                </p>
              )}
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Sanity checks on resource data, economics, and royalties
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleRunSanityCheck}
              disabled={sanityLoading}
            >
              {sanityLoading ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Running…</> : "Re-run checks"}
            </button>
          </div>

          {sanityLoading && !sanity && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)" }}>
              <span className="spinner" style={{ width: 22, height: 22 }} />
            </div>
          )}

          {sanity && (() => {
            const overallLabel = sanity.overall === "no_data" ? "No data" : sanity.overall.charAt(0).toUpperCase() + sanity.overall.slice(1);
            const levelLabel: Record<string, string> = { critical: "Critical", warning: "Caution", ok: "Pass", info: "Info" };
            const allFlags = sanity.flags ?? [];

            return (
              <>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", marginBottom: 16, lineHeight: 1.7 }}>
                  Overall result: <strong>{overallLabel}</strong>
                  {sanity.critical_count > 0 ? ` · ${sanity.critical_count} critical item${sanity.critical_count !== 1 ? "s" : ""}` : ""}
                  {sanity.warning_count > 0 ? ` · ${sanity.warning_count} caution${sanity.warning_count !== 1 ? "s" : ""}` : ""}
                  {sanity.ok_count > 0 ? ` · ${sanity.ok_count} passed` : ""}
                </p>
                {allFlags.length > 0 && (
                  <div style={{ overflowX: "auto" }}>
                    <table className="details-param-table" style={{ width: "100%" }}>
                      <thead>
                        <tr>
                          <th>Check</th>
                          <th>Value</th>
                          <th>Finding</th>
                          <th>Expected</th>
                          <th>Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allFlags.map((f, i) => (
                          <tr key={i}>
                            <td style={{ fontWeight: 500 }}>{f.field}</td>
                            <td style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-secondary)" }}>{f.value ?? "—"}</td>
                            <td style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>{f.message}</td>
                            <td style={{ color: "var(--text-tertiary)", fontSize: 12 }}>{f.expected_range ?? "—"}</td>
                            <td style={{ whiteSpace: "nowrap", color: "var(--text-secondary)", fontSize: 12 }}>{levelLabel[f.level] ?? f.level}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            );
          })()}

          {!sanity && !sanityLoading && (
            <div className="empty-state">
              <h3>Run sanity checks</h3>
              <p>Checks grade ranges, contained metal consistency, economic plausibility, and royalty burden</p>
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={handleRunSanityCheck}>
                Run Checks
              </button>
            </div>
          )}
          </div>

          {/* Royalties */}
          <div className="details-section">
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 16 }}>
              <div className="details-section-heading" style={{ marginBottom: 0 }}>Royalties &amp; Encumbrances</div>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {royaltyList.length > 0 ? `${royaltyList.length} agreement${royaltyList.length !== 1 ? "s" : ""} extracted from documents` : "Extracted from uploaded documents on analysis"}
              </span>
            </div>

          {/* Warnings */}
          {royaltySummary && royaltySummary.warnings.length > 0 && (
            <ul style={{ margin: "0 0 20px", paddingLeft: 20, fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.8 }}>
              {royaltySummary.warnings.map((w, i) => (
                <li key={i}>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {w.level === "critical" ? "Critical" : w.level === "caution" ? "Caution" : "Note"}:{" "}
                  </span>
                  {w.message}
                </li>
              ))}
            </ul>
          )}

          {/* Royalties table — primary display */}
          {royaltyList.length > 0 ? (
            <div style={{ overflowX: "auto", marginBottom: 16 }}>
              <table className="details-param-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    {["Type", "Holder", "Rate / Terms", "Metals", "Area", "Notes", ""].map(h => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {royaltyList.map((r) => (
                    <tr key={r.royalty_id}>
                      <td style={{ whiteSpace: "nowrap", fontWeight: 600 }}>{r.royalty_type}</td>
                      <td style={{ fontWeight: 500 }}>
                        {r.holder}
                        {r.buyback_option && <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 400 }}>Buyback option{r.buyback_price_musd ? ` · $${r.buyback_price_musd}M` : ""}</span>}
                      </td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {r.rate_pct != null ? `${r.rate_pct}%` : ""}
                        {r.stream_pct != null ? `${r.stream_pct}% @ ${r.stream_purchase_price ?? "—"} ${r.stream_purchase_unit ?? ""}` : ""}
                        {r.production_rate != null ? `${r.production_rate} ${r.production_unit ?? ""}/unit` : ""}
                        {r.sliding_scale_notes ? <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)" }}>{r.sliding_scale_notes}</span> : ""}
                      </td>
                      <td style={{ color: "var(--text-secondary)" }}>{r.metals_covered ?? "—"}</td>
                      <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>{r.area_covered ?? "—"}</td>
                      <td style={{ color: "var(--text-secondary)", fontSize: 12, fontStyle: "italic" }}>{r.notes ?? r.recorded_instrument ?? "—"}</td>
                      <td style={{ width: 32 }}>
                        <button className="btn-icon-only" title="Remove" onClick={() => handleDeleteRoyalty(r.royalty_id)}><TrashIcon /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 13.5, color: "var(--text-tertiary)", fontStyle: "italic", marginBottom: 16 }}>
              No royalties or streams found in uploaded documents. Run an analysis to extract them automatically, or add one manually below.
            </p>
          )}

          {/* Secondary: manual add */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowRoyaltyForm(v => !v)}>
              {showRoyaltyForm ? "Cancel" : "+ Add / Correct Manually"}
            </button>
          </div>
          {showRoyaltyForm && (
            <form onSubmit={handleAddRoyalty} style={{ marginTop: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
                <div>
                  <label className="form-label">Type *</label>
                  <select className="form-input" style={{ fontSize: 13 }} required
                    value={royaltyForm.royalty_type ?? "NSR"}
                    onChange={(e) => setRoyaltyForm(f => ({ ...f, royalty_type: e.target.value as Royalty["royalty_type"] }))}>
                    {["NSR", "GR", "NPI", "Stream", "Sliding NSR", "Production", "Other"].map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="form-label">Holder *</label>
                  <input className="form-input" style={{ fontSize: 13 }} required value={royaltyForm.holder ?? ""}
                    onChange={(e) => setRoyaltyForm(f => ({ ...f, holder: e.target.value }))} placeholder="Franco-Nevada, Wheaton…" />
                </div>
                <div>
                  <label className="form-label">Metals Covered</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={royaltyForm.metals_covered ?? ""}
                    onChange={(e) => setRoyaltyForm(f => ({ ...f, metals_covered: e.target.value || null }))} placeholder="Gold, Silver, All…" />
                </div>
                {["NSR", "GR", "NPI", "Sliding NSR"].includes(royaltyForm.royalty_type ?? "NSR") && (
                  <div>
                    <label className="form-label">Rate (%)</label>
                    <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.01"
                      value={royaltyForm.rate_pct ?? ""}
                      onChange={(e) => setRoyaltyForm(f => ({ ...f, rate_pct: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 2.0" />
                  </div>
                )}
                {royaltyForm.royalty_type === "Stream" && (<>
                  <div><label className="form-label">Stream %</label>
                    <input className="form-input" style={{ fontSize: 13 }} type="number" value={royaltyForm.stream_pct ?? ""}
                      onChange={(e) => setRoyaltyForm(f => ({ ...f, stream_pct: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 20" /></div>
                  <div><label className="form-label">Purchase Price</label>
                    <input className="form-input" style={{ fontSize: 13 }} type="number" value={royaltyForm.stream_purchase_price ?? ""}
                      onChange={(e) => setRoyaltyForm(f => ({ ...f, stream_purchase_price: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 400" /></div>
                  <div><label className="form-label">Unit</label>
                    <input className="form-input" style={{ fontSize: 13 }} value={royaltyForm.stream_purchase_unit ?? ""}
                      onChange={(e) => setRoyaltyForm(f => ({ ...f, stream_purchase_unit: e.target.value || null }))} placeholder="USD/oz" /></div>
                </>)}
                <div style={{ gridColumn: "span 3" }}>
                  <label className="form-label">Notes</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={royaltyForm.notes ?? ""}
                    onChange={(e) => setRoyaltyForm(f => ({ ...f, notes: e.target.value || null }))} placeholder="Context, caveats, source…" />
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                <button type="button" className="btn btn-secondary btn-sm"
                  onClick={() => { setShowRoyaltyForm(false); setRoyaltyForm({ royalty_type: "NSR", buyback_option: false }); }}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={royaltyLoading || !royaltyForm.holder?.trim()}>
                  {royaltyLoading ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "Save"}
                </button>
              </div>
            </form>
          )}
          </div>

          {/* Resources */}
          <div className="details-section">
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 16 }}>
              <div className="details-section-heading" style={{ marginBottom: 0 }}>Resource Estimates</div>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {resources.length > 0 ? `${resources.length} row${resources.length !== 1 ? "s" : ""} extracted from documents` : "Extracted from uploaded documents on analysis"}
              </span>
            </div>

          {/* Warnings */}
          {resourceSummary && resourceSummary.warnings.length > 0 && (
            <ul style={{ margin: "0 0 16px", paddingLeft: 20, fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.8 }}>
              {resourceSummary.warnings.map((w, i) => (
                <li key={i}>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                    {w.level === "critical" ? "Critical" : w.level === "caution" ? "Caution" : "Note"}:{" "}
                  </span>
                  {w.message}
                </li>
              ))}
            </ul>
          )}

          {/* Resource table — primary display */}
          {resources.length > 0 ? (
            <div style={{ overflowX: "auto", marginBottom: 16 }}>
              <table className="details-param-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    {["Classification", "Domain", "Tonnage (Mt)", "Grade", "Unit", "Cut-off", "Contained", "Metal Unit", ""].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {resources.map((row) => (
                    <tr key={row.row_id}>
                      <td style={{ fontWeight: 600 }}>{row.classification}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{row.domain ?? "—"}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{row.tonnage_mt != null ? row.tonnage_mt.toLocaleString() : "—"}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{row.grade_value != null ? row.grade_value : "—"}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{row.grade_unit ?? "—"}</td>
                      <td style={{ color: "var(--text-secondary)", fontSize: 12 }}>{row.cut_off_grade ?? "—"}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>{row.contained_metal != null ? row.contained_metal.toLocaleString() : "—"}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{row.metal_unit ?? "—"}</td>
                      <td style={{ width: 32 }}>
                        <button className="btn-icon-only" title="Remove row" onClick={() => handleDeleteResource(row.row_id)}><TrashIcon /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                {resources.length > 1 && resourceSummary && (
                  <tfoot>
                    <tr>
                      <td colSpan={2} style={{ fontWeight: 700, fontSize: 12 }}>Total</td>
                      <td style={{ textAlign: "right", fontWeight: 700 }}>{resourceSummary.total_tonnage_mt != null ? resourceSummary.total_tonnage_mt.toLocaleString() : "—"}</td>
                      <td colSpan={3} />
                      <td style={{ textAlign: "right", fontWeight: 700 }}>{resourceSummary.total_contained != null ? resourceSummary.total_contained.toLocaleString() : "—"}</td>
                      <td colSpan={2} />
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 13.5, color: "var(--text-tertiary)", fontStyle: "italic", marginBottom: 16 }}>
              No resource estimates found in uploaded documents. Run an analysis to extract them automatically, or add a row manually below.
            </p>
          )}

          {/* Secondary: manual add */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowResForm(v => !v)}>
              {showResForm ? "Cancel" : "+ Add / Correct Row Manually"}
            </button>
          </div>
          {showResForm && (
            <form onSubmit={handleAddResource} style={{ marginTop: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
                <div>
                  <label className="form-label">Classification *</label>
                  <select className="form-input" style={{ fontSize: 13 }} required
                    value={resForm.classification ?? "Measured"}
                    onChange={(e) => setResForm((f) => ({ ...f, classification: e.target.value as ResourceRow["classification"] }))}>
                    <option>Measured</option><option>Indicated</option><option>Inferred</option>
                  </select>
                </div>
                <div><label className="form-label">Domain</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={resForm.domain ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, domain: e.target.value || null }))} placeholder="oxide, sulphide…" /></div>
                <div><label className="form-label">Tonnage (Mt)</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.001" value={resForm.tonnage_mt ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, tonnage_mt: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 45.2" /></div>
                <div><label className="form-label">Grade</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.001" value={resForm.grade_value ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, grade_value: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 1.24" /></div>
                <div><label className="form-label">Grade Unit</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={resForm.grade_unit ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, grade_unit: e.target.value || null }))} placeholder="g/t, %, ppm…" /></div>
                <div><label className="form-label">Contained Metal</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.01" value={resForm.contained_metal ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, contained_metal: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 2.4" /></div>
                <div><label className="form-label">Metal Unit</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={resForm.metal_unit ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, metal_unit: e.target.value || null }))} placeholder="Moz, Mlb, kt…" /></div>
                <div><label className="form-label">Cut-off Grade</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={resForm.cut_off_grade ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, cut_off_grade: e.target.value || null }))} placeholder="e.g. 0.3 g/t Au" /></div>
                <div><label className="form-label">Notes</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={resForm.notes ?? ""}
                    onChange={(e) => setResForm((f) => ({ ...f, notes: e.target.value || null }))} placeholder="Optional" /></div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setShowResForm(false); setResForm({ classification: "Measured" }); }}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={resLoading}>
                  {resLoading ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "Save Row"}
                </button>
              </div>
            </form>
          )}
          </div>

          {/* Comparable Transactions */}
          <div className="details-section">
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 16 }}>
              <div className="details-section-heading" style={{ marginBottom: 0 }}>Comparable Transactions</div>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                {comps.length > 0 ? `${comps.length} transaction${comps.length !== 1 ? "s" : ""} extracted from documents` : "Extracted from uploaded documents on analysis"}
              </span>
            </div>

          {/* Comps table — primary display */}
          {comps.length > 0 ? (
            <div style={{ overflowX: "auto", marginBottom: 16 }}>
              <table className="details-param-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    {["Project / Asset", "Commodity", "Date", "Stage", "Deal (M USD)", "Resource", "$/unit", "Jurisdiction", ""].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comps.map((c) => (
                    <tr key={c.comp_id}>
                      <td style={{ fontWeight: 500 }}>
                        {c.project_name}
                        {(c.acquirer || c.seller) && (
                          <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", fontWeight: 400 }}>
                            {[c.acquirer, c.seller].filter(Boolean).join(" ← ")}
                          </span>
                        )}
                        {c.notes && <span style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", fontStyle: "italic" }}>{c.notes}</span>}
                      </td>
                      <td style={{ color: "var(--text-secondary)" }}>{c.commodity ?? "—"}</td>
                      <td style={{ color: "var(--text-secondary)", whiteSpace: "nowrap" }}>{c.transaction_date ?? "—"}</td>
                      <td style={{ color: "var(--text-secondary)" }}>{c.study_stage ?? "—"}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {c.transaction_value_musd != null ? `$${c.transaction_value_musd.toLocaleString()}M` : "—"}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                        {c.resource_moz_or_mlb != null ? `${c.resource_moz_or_mlb}M` : "—"}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                        {c.price_per_unit_usd != null ? `$${c.price_per_unit_usd.toLocaleString()}` : "—"}
                      </td>
                      <td style={{ color: "var(--text-secondary)" }}>{c.jurisdiction ?? "—"}</td>
                      <td style={{ width: 32 }}>
                        <button className="btn-icon-only" title="Remove" onClick={() => handleDeleteComp(c.comp_id)}><TrashIcon /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ fontSize: 13.5, color: "var(--text-tertiary)", fontStyle: "italic", marginBottom: 16 }}>
              No comparable transactions found in uploaded documents. Run an analysis to extract them automatically, or add one manually below.
            </p>
          )}

          {/* Secondary: manual add */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowCompForm(v => !v)}>
              {showCompForm ? "Cancel" : "+ Add / Correct Manually"}
            </button>
          </div>
          {showCompForm && (
            <form onSubmit={handleAddComp} style={{ marginTop: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                <div><label className="form-label">Project / Asset Name *</label>
                  <input className="form-input" style={{ fontSize: 13 }} required value={compForm.project_name ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, project_name: e.target.value }))} placeholder="e.g. Snowline Raven Gold" /></div>
                <div><label className="form-label">Commodity</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.commodity ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, commodity: e.target.value }))} placeholder="Gold, Copper…" /></div>
                <div><label className="form-label">Acquirer</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.acquirer ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, acquirer: e.target.value }))} placeholder="Buyer" /></div>
                <div><label className="form-label">Seller</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.seller ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, seller: e.target.value }))} placeholder="Vendor" /></div>
                <div><label className="form-label">Date</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.transaction_date ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, transaction_date: e.target.value }))} placeholder="2024 or 2024-03" /></div>
                <div><label className="form-label">Stage</label>
                  <select className="form-input" style={{ fontSize: 13 }} value={compForm.study_stage ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, study_stage: e.target.value || null }))}>
                    <option value="">—</option><option>PEA</option><option>PFS</option><option>FS</option><option>Producing</option><option>Exploration</option>
                  </select></div>
                <div><label className="form-label">Deal Value (M USD)</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.1" value={compForm.transaction_value_musd ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, transaction_value_musd: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 450" /></div>
                <div><label className="form-label">Resource (Moz/Mlb)</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.01" value={compForm.resource_moz_or_mlb ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, resource_moz_or_mlb: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="Total M+I+Inf" /></div>
                <div><label className="form-label">Implied $/oz or $/lb</label>
                  <input className="form-input" style={{ fontSize: 13 }} type="number" min="0" step="0.01" value={compForm.price_per_unit_usd ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, price_per_unit_usd: e.target.value ? parseFloat(e.target.value) : null }))} placeholder="e.g. 85" /></div>
                <div><label className="form-label">Jurisdiction</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.jurisdiction ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, jurisdiction: e.target.value }))} placeholder="Canada, Australia…" /></div>
                <div style={{ gridColumn: "span 2" }}><label className="form-label">Notes</label>
                  <input className="form-input" style={{ fontSize: 13 }} value={compForm.notes ?? ""}
                    onChange={(e) => setCompForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Any context or caveats" /></div>
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setShowCompForm(false); setCompForm({}); }}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={compLoading || !compForm.project_name?.trim()}>
                  {compLoading ? <span className="spinner" style={{ width: 12, height: 12 }} /> : "Save"}
                </button>
              </div>
            </form>
          )}
          </div>

          {/* Run History */}
          <div className="details-section">
            <div className="details-section-heading">Run History</div>
          {runs.length === 0 ? (
            <div className="empty-state">
              <h3>No runs yet</h3>
              <p>Upload files and click "Run Analysis" to generate your first report</p>
            </div>
          ) : (
            <div className="run-panel">
              {runs.map((r) => (
                <div key={r.run_id} className="run-row">
                  <RunBadge status={r.status} />
                  <span className="run-id">{r.run_id}</span>
                  <span className="run-step">{r.error ?? r.step ?? ""}</span>
                  <span className="run-time">
                    {r.completed_at
                      ? new Date(r.completed_at).toLocaleString()
                      : r.started_at
                      ? new Date(r.started_at).toLocaleString()
                      : ""}
                  </span>
                  {r.status === "complete" && (
                    <Link
                      to={`/projects/${id}/report/${r.run_id}`}
                      className="btn btn-secondary btn-sm"
                    >
                      View Report
                    </Link>
                  )}
                  {r.status !== "running" && r.status !== "pending" && (
                    <button
                      className="btn-icon-only"
                      onClick={() => handleDeleteRun(r.run_id)}
                      title="Delete run"
                    >
                      <TrashIcon />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          </div>

          {/* News */}
          <div className="details-section">
            <div className="details-section-heading">Market News</div>
          {/* Header row */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15 }}>News &amp; Market Intelligence</div>
              {newsFeed && (
                <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 2 }}>
                  Last updated {new Date(newsFeed.fetched_at).toLocaleString()} · {newsFeed.project_name} · {newsFeed.commodity}
                  {newsFeed.jurisdiction ? ` · ${newsFeed.jurisdiction}` : ""}
                </div>
              )}
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={async () => {
                setNewsRefreshing(true);
                try {
                  const feed = await refreshProjectNews(id);
                  setNewsFeed(feed);
                } catch {
                  // swallow
                } finally {
                  setNewsRefreshing(false);
                }
              }}
              disabled={newsRefreshing}
            >
              {newsRefreshing
                ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Refreshing…</>
                : "↻ Refresh"}
            </button>
          </div>

          {/* Loading state */}
          {(newsLoading || newsRefreshing) && !newsFeed && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)" }}>
              <span className="spinner" style={{ width: 20, height: 20, display: "inline-block" }} />
              <div style={{ marginTop: 10, fontSize: 13 }}>Searching for news…</div>
            </div>
          )}

          {/* Error state */}
          {newsFeed?.error && (
            <div style={{ background: "#fff0f0", border: "1px solid #fecaca", borderRadius: 6, padding: "10px 14px", marginBottom: 16, fontSize: 13, color: "#dc3535" }}>
              ⚠ {newsFeed.error}
            </div>
          )}

          {/* Empty state */}
          {newsFeed && !newsFeed.error && newsFeed.items.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)" }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>📰</div>
              <div style={{ fontSize: 14, marginBottom: 4 }}>No news items yet</div>
              <div style={{ fontSize: 12 }}>Click Refresh to search for recent news</div>
            </div>
          )}

          {/* No feed yet */}
          {!newsFeed && !newsLoading && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-tertiary)" }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>📰</div>
              <div style={{ fontSize: 14, marginBottom: 4 }}>No news loaded</div>
              <div style={{ fontSize: 12 }}>Click Refresh to search for recent news about this project</div>
            </div>
          )}

          {/* News items */}
          {newsFeed && newsFeed.items.length > 0 && (() => {
            const CATEGORY_LABELS: Record<string, string> = {
              resource_update: "Resource Update", financing: "Financing", permitting: "Permitting",
              acquisition: "M&A", production: "Production", management: "Management",
              esg: "ESG", market: "Market", other: "Other",
            };
            const RELEVANCE_DOT: Record<string, string> = {
              high: "#0071e3", medium: "#8e8e93", low: "#c7c7cc",
            };
            const RELEVANCE_LABEL: Record<string, string> = {
              high: "High relevance", medium: "Medium relevance", low: "Sector context",
            };

            return (
              <div style={{ display: "flex", flexDirection: "column" }}>
                {newsFeed.items.map((item: NewsItem, idx: number) => {
                  const isExpanded = expandedNewsIds.has(item.news_id);
                  const hasSummary = item.summary &&
                    !item.summary.trim().startsWith("{") &&
                    !item.summary.trim().startsWith("[");
                  const toggle = () => setExpandedNewsIds(prev => {
                    const next = new Set(prev);
                    if (next.has(item.news_id)) next.delete(item.news_id);
                    else next.add(item.news_id);
                    return next;
                  });

                  return (
                    <div
                      key={item.news_id}
                      style={{
                        padding: "14px 0",
                        borderBottom: idx < newsFeed.items.length - 1 ? "1px solid var(--border)" : "none",
                      }}
                    >
                      {/* Headline row */}
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 5 }}>
                        {/* Relevance dot */}
                        <span
                          title={RELEVANCE_LABEL[item.relevance] ?? item.relevance}
                          style={{
                            flexShrink: 0, marginTop: 5,
                            width: 7, height: 7, borderRadius: "50%",
                            background: RELEVANCE_DOT[item.relevance] ?? RELEVANCE_DOT.medium,
                          }}
                        />
                        <div style={{ flex: 1, fontWeight: 600, fontSize: 14, lineHeight: 1.45 }}>
                          {item.headline}
                        </div>
                      </div>

                      {/* Meta line */}
                      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: hasSummary ? 6 : 0, paddingLeft: 17, display: "flex", flexWrap: "wrap", gap: "0 6px" }}>
                        {item.date && <span>{item.date}</span>}
                        {item.source && <><span>·</span><span style={{ fontStyle: "italic" }}>{item.source}</span></>}
                        {item.category && <><span>·</span><span>{CATEGORY_LABELS[item.category] ?? item.category}</span></>}
                        {item.sentiment && item.sentiment !== "neutral" && (
                          <><span>·</span><span>{item.sentiment === "positive" ? "Positive" : "Negative"}</span></>
                        )}
                      </div>

                      {/* Expand / collapse summary + article link */}
                      {hasSummary && (
                        <div style={{ paddingLeft: 17 }}>
                          <button
                            onClick={toggle}
                            style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontSize: 12, color: "var(--accent)", display: "flex", alignItems: "center", gap: 4 }}
                          >
                            <span style={{ fontSize: 10, transform: isExpanded ? "rotate(90deg)" : "none", display: "inline-block", transition: "transform 0.15s" }}>▶</span>
                            {isExpanded ? "Hide summary" : "Read AI summary"}
                          </button>
                          {isExpanded && (
                            <div style={{ marginTop: 8, fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                              {item.summary}
                              {item.url && (
                                <div style={{ marginTop: 8 }}>
                                  <a href={item.url} target="_blank" rel="noopener noreferrer"
                                    style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}
                                    onMouseOver={e => (e.currentTarget.style.textDecoration = "underline")}
                                    onMouseOut={e => (e.currentTarget.style.textDecoration = "none")}>
                                    Read full article →
                                  </a>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                      {/* No summary but has URL */}
                      {!hasSummary && item.url && (
                        <div style={{ paddingLeft: 17, marginTop: 4 }}>
                          <a href={item.url} target="_blank" rel="noopener noreferrer"
                            style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none" }}
                            onMouseOver={e => (e.currentTarget.style.textDecoration = "underline")}
                            onMouseOut={e => (e.currentTarget.style.textDecoration = "none")}>
                            Read article →
                          </a>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })()}
          </div>

          {/* Drillholes */}
          {dhDataset && dhDataset.hole_count > 0 && (
          <div className="details-section">
            <div className="details-section-heading">Drill Hole Data</div>
          {(() => {
            const dataset = dhDataset!;
            const collars = dataset.collars;
            const assays  = dataset.assays;
            const traces  = dataset.traces;
            const analytes = dataset.analytes;
            const selectedAnalyte = dhAnalyte || analytes[0] || "";

            // ── Assay lookup: {hole_id → sorted assay rows}
            const assaysByHole: Record<string, typeof assays> = {};
            for (const a of assays) {
              if (!assaysByHole[a.hole_id]) assaysByHole[a.hole_id] = [];
              assaysByHole[a.hole_id].push(a);
            }

            // ── Analyte colour scale (white → gold orange → red)
            const allVals = assays.map(a => Number(a[selectedAnalyte])).filter(v => !isNaN(v) && v > 0);
            const maxVal = allVals.length ? Math.max(...allVals) : 1;
            const p95 = allVals.length
              ? [...allVals].sort((a, b) => a - b)[Math.floor(allVals.length * 0.95)] || maxVal
              : maxVal;

            function gradeColor(v: number | null | undefined): string {
              if (v == null || isNaN(Number(v)) || Number(v) <= 0) return "#e5e7eb";
              const t = Math.min(1, Number(v) / (p95 || maxVal || 1));
              // White → amber → red
              if (t < 0.5) {
                const s = t * 2;
                const r = Math.round(255);
                const g = Math.round(255 - s * (255 - 160));
                const b = Math.round(255 - s * 255);
                return `rgb(${r},${g},${b})`;
              } else {
                const s = (t - 0.5) * 2;
                const r = Math.round(255);
                const g = Math.round(160 - s * 160);
                const b = 0;
                return `rgb(${r},${g},${b})`;
              }
            }

            // ── Plan view: normalise XY to SVG space
            const PLAN_W = 520, PLAN_H = 360, PLAN_PAD = 36;
            const xs = collars.map(c => c.x).filter((v): v is number => v != null);
            const ys = collars.map(c => c.y).filter((v): v is number => v != null);
            const hasXY = xs.length > 0 && ys.length > 0;

            let planScale = 1, planOX = PLAN_PAD, planOY = PLAN_PAD;
            if (hasXY) {
              const xMin = Math.min(...xs), xMax = Math.max(...xs);
              const yMin = Math.min(...ys), yMax = Math.max(...ys);
              const xRange = xMax - xMin || 1, yRange = yMax - yMin || 1;
              const scaleX = (PLAN_W - PLAN_PAD * 2) / xRange;
              const scaleY = (PLAN_H - PLAN_PAD * 2) / yRange;
              planScale = Math.min(scaleX, scaleY);
              planOX = PLAN_PAD + ((PLAN_W - PLAN_PAD * 2) - xRange * planScale) / 2;
              planOY = PLAN_PAD + ((PLAN_H - PLAN_PAD * 2) - yRange * planScale) / 2 + yRange * planScale;
            }

            function toSvgX(x: number): number {
              const xMin = Math.min(...xs);
              return planOX + (x - xMin) * planScale;
            }
            function toSvgY(y: number): number {
              const yMin = Math.min(...ys);
              return planOY - (y - yMin) * planScale;
            }

            const selectedHole = dhSelectedHole;
            const selectedTrace: TracePoint[] = selectedHole ? (traces[selectedHole] || []) : [];
            const selectedAssays = selectedHole ? (assaysByHole[selectedHole] || []) : [];
            const maxDepth = selectedAssays.length
              ? Math.max(...selectedAssays.map(a => a.to_m || 0))
              : (collars.find(c => c.hole_id === selectedHole)?.depth || 0);

            const LOG_W = 220, LOG_H = 440, LOG_PAD_T = 32, LOG_DEPTH_COL = 38, LOG_BAR_X = 70, LOG_BAR_W = 100;
            const depthScale = maxDepth > 0 ? (LOG_H - LOG_PAD_T - 10) / maxDepth : 1;

            return (
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                {/* Left: plan view */}
                <div style={{ flex: "0 0 auto", minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                    Plan View · {collars.length} holes
                  </div>
                  <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", background: "#f8f9fa", display: "inline-block" }}>
                    {hasXY ? (
                      <svg width={PLAN_W} height={PLAN_H} style={{ display: "block" }}>
                        {/* Traces */}
                        {Object.entries(traces).map(([hid, trace]) => {
                          if (trace.length < 2) return null;
                          const pts = trace.map(p => `${toSvgX(p.x)},${toSvgY(p.y)}`).join(" ");
                          return (
                            <polyline key={hid} points={pts} fill="none"
                              stroke={hid === selectedHole ? "#2C4A3E" : "#9ca3af"}
                              strokeWidth={hid === selectedHole ? 2 : 1}
                              opacity={hid === selectedHole ? 1 : 0.5}
                            />
                          );
                        })}
                        {/* Collar dots */}
                        {collars.map(c => {
                          if (c.x == null || c.y == null) return null;
                          const cx = toSvgX(c.x), cy = toSvgY(c.y);
                          const sel = c.hole_id === selectedHole;
                          return (
                            <g key={c.hole_id} onClick={() => setDhSelectedHole(sel ? null : c.hole_id)} style={{ cursor: "pointer" }}>
                              <circle cx={cx} cy={cy} r={sel ? 7 : 5}
                                fill={sel ? "#2C4A3E" : "#6b7280"}
                                stroke="white" strokeWidth={sel ? 2 : 1}
                              />
                              <text x={cx + 8} y={cy + 4} fontSize={sel ? 11 : 9}
                                fill={sel ? "#2C4A3E" : "#374151"} fontWeight={sel ? "bold" : "normal"}>
                                {c.hole_id}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    ) : (
                      <div style={{ width: PLAN_W, height: PLAN_H, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", color: "var(--text-tertiary)", gap: 8 }}>
                        <div style={{ fontSize: 28 }}>📍</div>
                        <div style={{ fontSize: 13 }}>{collars.length} holes loaded</div>
                        <div style={{ fontSize: 11 }}>No X/Y coordinates — upload a collars file with Easting/Northing</div>
                      </div>
                    )}
                  </div>

                  {/* Collar table below plan */}
                  <div style={{ marginTop: 12, maxHeight: 160, overflowY: "auto" }}>
                    <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "var(--bg-secondary)" }}>
                          {["Hole ID", "X", "Y", "Z", "Depth (m)", "Az°", "Dip°"].map(h => (
                            <th key={h} style={{ padding: "4px 8px", textAlign: "left", fontWeight: 600, color: "var(--text-tertiary)", borderBottom: "1px solid var(--border)" }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {collars.map(c => (
                          <tr key={c.hole_id}
                            onClick={() => setDhSelectedHole(c.hole_id === dhSelectedHole ? null : c.hole_id)}
                            style={{ cursor: "pointer", background: c.hole_id === dhSelectedHole ? "#f0fdf4" : "transparent" }}>
                            <td style={{ padding: "3px 8px", fontWeight: 600, color: "var(--text-primary)" }}>{c.hole_id}</td>
                            {[c.x, c.y, c.z, c.depth, c.azimuth, c.dip].map((v, i) => (
                              <td key={i} style={{ padding: "3px 8px", color: "var(--text-secondary)", fontFamily: "monospace" }}>
                                {v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "—"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Right: strip log for selected hole */}
                {selectedHole && (
                  <div style={{ flex: "1 1 auto", minWidth: 260 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        {selectedHole} — Downhole Log
                      </div>
                      {analytes.length > 1 && (
                        <select
                          className="form-input"
                          style={{ fontSize: 12, padding: "2px 8px", width: "auto" }}
                          value={selectedAnalyte}
                          onChange={e => setDhAnalyte(e.target.value)}
                        >
                          {analytes.map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}
                        </select>
                      )}
                    </div>

                    {selectedAssays.length === 0 ? (
                      <div style={{ padding: "20px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
                        No assay intervals loaded for this hole.
                      </div>
                    ) : (
                      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                        {/* SVG strip log */}
                        <svg width={LOG_W} height={LOG_H} style={{ flex: "0 0 auto", border: "1px solid var(--border)", borderRadius: 6, background: "#fff" }}>
                          {/* Axis label */}
                          <text x={LOG_DEPTH_COL - 2} y={14} fontSize={9} fill="#9ca3af" textAnchor="middle">m</text>
                          <text x={LOG_BAR_X + LOG_BAR_W / 2} y={14} fontSize={9} fill="#9ca3af" textAnchor="middle">{selectedAnalyte.toUpperCase()}</text>

                          {/* Depth ticks */}
                          {Array.from({ length: Math.ceil(maxDepth / 50) + 1 }, (_, i) => i * 50).map(d => {
                            if (d > maxDepth + 5) return null;
                            const y = LOG_PAD_T + d * depthScale;
                            return (
                              <g key={d}>
                                <line x1={LOG_DEPTH_COL + 8} y1={y} x2={LOG_BAR_X + LOG_BAR_W + 4} y2={y} stroke="#e5e7eb" strokeWidth={1} />
                                <text x={LOG_DEPTH_COL + 5} y={y + 3} fontSize={8.5} fill="#9ca3af" textAnchor="end">{d}</text>
                              </g>
                            );
                          })}

                          {/* Assay intervals */}
                          {selectedAssays.map((a, i) => {
                            const f = a.from_m ?? 0;
                            const t = a.to_m ?? f;
                            const y1 = LOG_PAD_T + f * depthScale;
                            const h  = Math.max(1, (t - f) * depthScale);
                            const v  = a[selectedAnalyte] as number | undefined;
                            return (
                              <g key={i}>
                                <rect x={LOG_BAR_X} y={y1} width={LOG_BAR_W} height={h}
                                  fill={gradeColor(v as number)}
                                  stroke="#e5e7eb" strokeWidth={0.3}
                                />
                                {h > 14 && v != null && (
                                  <text x={LOG_BAR_X + LOG_BAR_W + 4} y={y1 + h / 2 + 3}
                                    fontSize={8} fill="#374151">
                                    {Number(v).toFixed(Number(v) < 10 ? 2 : 1)}
                                  </text>
                                )}
                              </g>
                            );
                          })}

                          {/* EOH line */}
                          {maxDepth > 0 && (
                            <line x1={LOG_BAR_X - 4} y1={LOG_PAD_T + maxDepth * depthScale}
                              x2={LOG_BAR_X + LOG_BAR_W + 4} y2={LOG_PAD_T + maxDepth * depthScale}
                              stroke="#374151" strokeWidth={1.5} strokeDasharray="4,2"
                            />
                          )}
                        </svg>

                        {/* Assay table */}
                        <div style={{ flex: 1, overflowY: "auto", maxHeight: LOG_H }}>
                          <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                            <thead>
                              <tr style={{ background: "var(--bg-secondary)", position: "sticky", top: 0 }}>
                                <th style={{ padding: "3px 6px", textAlign: "right", color: "var(--text-tertiary)", fontWeight: 600 }}>From</th>
                                <th style={{ padding: "3px 6px", textAlign: "right", color: "var(--text-tertiary)", fontWeight: 600 }}>To</th>
                                <th style={{ padding: "3px 6px", textAlign: "right", color: "var(--text-tertiary)", fontWeight: 600 }}>{selectedAnalyte.toUpperCase()}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedAssays.map((a, i) => {
                                const v = a[selectedAnalyte] as number | undefined;
                                return (
                                  <tr key={i} style={{ background: i % 2 ? "var(--bg-secondary)" : "transparent" }}>
                                    <td style={{ padding: "2px 6px", textAlign: "right", fontFamily: "monospace" }}>{a.from_m?.toFixed(1)}</td>
                                    <td style={{ padding: "2px 6px", textAlign: "right", fontFamily: "monospace" }}>{a.to_m?.toFixed(1)}</td>
                                    <td style={{ padding: "2px 6px", textAlign: "right", fontFamily: "monospace", fontWeight: v != null && v > p95 * 0.5 ? 700 : 400, color: v != null && v > p95 * 0.5 ? "#92400e" : "inherit" }}>
                                      {v != null ? v.toFixed(Number(v) < 10 ? 2 : 1) : "—"}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Significant intercepts */}
                    {selectedAssays.length > 0 && p95 > 0 && (() => {
                      const cuts = selectedAssays.filter(a => (a[selectedAnalyte] as number) >= p95 * 0.5);
                      if (!cuts.length) return null;
                      const best = cuts.reduce((best, a) => ((a[selectedAnalyte] as number) > (best[selectedAnalyte] as number) ? a : best), cuts[0]);
                      return (
                        <div style={{ marginTop: 12, padding: "8px 12px", background: "#fef9c3", border: "1px solid #fde68a", borderRadius: 6, fontSize: 12 }}>
                          <span style={{ fontWeight: 700, color: "#92400e" }}>Best intercept: </span>
                          <span style={{ color: "#78350f" }}>
                            {best.from_m?.toFixed(1)}m – {best.to_m?.toFixed(1)}m = {Number(best[selectedAnalyte]).toFixed(2)} {selectedAnalyte.toUpperCase()}
                            {best.length ? ` over ${best.length.toFixed(1)}m` : ""}
                          </span>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            );
          })()}
          </div>
          )}
        </div>
      )}
    </>
  );
}
