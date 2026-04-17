import { useEffect, useRef, useState } from "react";
import { registerDropZone, unregisterDropZone } from "../../lib/tauriFileDrop";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

interface Capabilities {
  cad_pack: boolean;
  omf_pack: boolean;
  upgrade_info: {
    cad: { name: string; description: string; formats: string[] };
    geo: { name: string; description: string; formats: string[] };
  };
}

const BASE_FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG/JPG", "DXF"];
const CAD_FORMATS  = ["STEP", "IGES", "BREP"];
const GEO_FORMATS  = ["OMF", "VTK", "OBJ", "STL"];

const BASE_ACCEPT = ".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg,.tiff,.dxf,.dwg";
const CAD_ACCEPT  = ".step,.stp,.iges,.igs,.brep";
const GEO_ACCEPT  = ".omf,.vtk,.vtu,.obj,.stl";

const isTauri = typeof window !== "undefined" && !!(window as any).__TAURI__;

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}>
      <path d="M10 13V7M10 7L7 10M10 7l3 3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 14a4 4 0 010-8h.5M17 14a4 4 0 000-8h-.5" strokeLinecap="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M11 7V5a3 3 0 10-6 0v2H3v8h10V7h-2zm-4-2a1 1 0 112 0v2H7V5z"/>
    </svg>
  );
}

export default function DropZone({ onFiles, disabled = false }: DropZoneProps) {
  const [dragOver, setDragOver]       = useState(false);
  const [caps, setCaps]               = useState<Capabilities | null>(null);
  const [upgradeTarget, setUpgrade]   = useState<"cad" | "geo" | null>(null);
  const inputRef     = useRef<HTMLInputElement>(null);
  const dragCounter  = useRef(0);
  const onFilesRef   = useRef(onFiles);
  const disabledRef  = useRef(disabled);
  useEffect(() => { onFilesRef.current = onFiles; }, [onFiles]);
  useEffect(() => { disabledRef.current = disabled; }, [disabled]);

  // Fetch capabilities once on mount
  useEffect(() => {
    fetch("http://localhost:8000/capabilities")
      .then(r => r.json())
      .then(setCaps)
      .catch(() => setCaps({ cad_pack: false, omf_pack: false, upgrade_info: {
        cad: { name: "CAD Analysis Pack", description: "", formats: CAD_FORMATS.map(f => f.toLowerCase()) },
        geo: { name: "Geology 3D Pack",   description: "", formats: GEO_FORMATS.map(f => f.toLowerCase()) },
      }}));
  }, []);

  // ── Tauri: singleton listener ────────────────────────────────────────────
  useEffect(() => {
    if (!isTauri) return;
    registerDropZone((files, hover) => {
      setDragOver(hover);
      if (files.length && !disabledRef.current) onFilesRef.current(files);
    });
    return () => unregisterDropZone();
  }, []);

  // ── Browser drag events ─────────────────────────────────────────────────
  function handleDragEnter(e: React.DragEvent) {
    if (isTauri) return;
    e.preventDefault();
    dragCounter.current += 1;
    if (!disabled) setDragOver(true);
  }
  function handleDragOver(e: React.DragEvent) { if (!isTauri) e.preventDefault(); }
  function handleDragLeave(e: React.DragEvent) {
    if (isTauri) return;
    e.preventDefault();
    dragCounter.current -= 1;
    if (dragCounter.current === 0) setDragOver(false);
  }
  function handleDrop(e: React.DragEvent) {
    if (isTauri) return;
    e.preventDefault();
    dragCounter.current = 0;
    setDragOver(false);
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files);
    if (files.length) onFiles(files);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
    e.target.value = "";
  }

  const cadPack = caps?.cad_pack ?? false;
  const omfPack = caps?.omf_pack ?? false;

  const acceptAttr = [
    BASE_ACCEPT,
    cadPack ? CAD_ACCEPT : "",
    omfPack ? GEO_ACCEPT : "",
  ].filter(Boolean).join(",");

  return (
    <>
      <div
        className={`drop-zone ${dragOver ? "drag-over" : ""}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        style={{ opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
      >
        <div className="drop-zone-inner">
          <UploadIcon />
          <div className="drop-zone-text">Drop files or <span className="drop-zone-link">click to browse</span></div>
          <div className="drop-zone-formats">
            {BASE_FORMATS.map(f => (
              <span key={f} className="format-chip">.{f.toLowerCase()}</span>
            ))}
            {CAD_FORMATS.map(f =>
              cadPack ? (
                <span key={f} className="format-chip">.{f.toLowerCase()}</span>
              ) : (
                <span
                  key={f}
                  className="format-chip format-chip--locked"
                  title="CAD Analysis Pack required"
                  onClick={e => { e.stopPropagation(); setUpgrade("cad"); }}
                >
                  <LockIcon />.{f.toLowerCase()}
                </span>
              )
            )}
            {GEO_FORMATS.map(f =>
              omfPack ? (
                <span key={f} className="format-chip">.{f.toLowerCase()}</span>
              ) : (
                <span
                  key={f}
                  className="format-chip format-chip--locked"
                  title="Geology 3D Pack required"
                  onClick={e => { e.stopPropagation(); setUpgrade("geo"); }}
                >
                  <LockIcon />.{f.toLowerCase()}
                </span>
              )
            )}
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          style={{ display: "none" }}
          onChange={handleChange}
          accept={acceptAttr}
        />
      </div>

      {upgradeTarget && caps && (
        <UpgradeModal
          info={caps.upgrade_info[upgradeTarget]}
          onClose={() => setUpgrade(null)}
        />
      )}
    </>
  );
}

function UpgradeModal({ info, onClose }: {
  info: { name: string; description: string; formats: string[] };
  onClose: () => void;
}) {
  return (
    <div className="upgrade-modal-overlay" onClick={onClose}>
      <div className="upgrade-modal" onClick={e => e.stopPropagation()}>
        <div className="upgrade-modal-header">
          <LockIcon />
          <span>{info.name}</span>
        </div>
        <p className="upgrade-modal-desc">{info.description}</p>
        <div className="upgrade-modal-formats">
          {info.formats.map(f => (
            <span key={f} className="format-chip">.{f}</span>
          ))}
        </div>
        <div className="upgrade-modal-actions">
          <a
            className="upgrade-modal-cta"
            href="https://extractapp.co/upgrade"
            target="_blank"
            rel="noreferrer"
          >
            Upgrade to unlock
          </a>
          <button className="upgrade-modal-dismiss" onClick={onClose}>Not now</button>
        </div>
      </div>
    </div>
  );
}
