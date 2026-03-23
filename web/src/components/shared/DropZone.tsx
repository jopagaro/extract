import { useEffect, useRef, useState } from "react";
import { registerDropZone, unregisterDropZone } from "../../lib/tauriFileDrop";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG/JPG", "DXF"];
const isTauri = typeof window !== "undefined" && !!(window as any).__TAURI__;

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}>
      <path d="M10 13V7M10 7L7 10M10 7l3 3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 14a4 4 0 010-8h.5M17 14a4 4 0 000-8h-.5" strokeLinecap="round" />
    </svg>
  );
}

export default function DropZone({ onFiles, disabled = false }: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);
  const onFilesRef = useRef(onFiles);
  const disabledRef = useRef(disabled);
  useEffect(() => { onFilesRef.current = onFiles; }, [onFiles]);
  useEffect(() => { disabledRef.current = disabled; }, [disabled]);

  // ── Tauri: use singleton listener ────────────────────────────────────────
  useEffect(() => {
    if (!isTauri) return;
    registerDropZone((files, hover) => {
      setDragOver(hover);
      if (files.length && !disabledRef.current) onFilesRef.current(files);
    });
    return () => unregisterDropZone();
  }, []);

  // ── Browser / dev: standard drag events ──────────────────────────────────
  function handleDragEnter(e: React.DragEvent) {
    if (isTauri) return;
    e.preventDefault();
    dragCounter.current += 1;
    if (!disabled) setDragOver(true);
  }
  function handleDragOver(e: React.DragEvent) {
    if (isTauri) return;
    e.preventDefault();
  }
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

  return (
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
          {FORMATS.map((f) => (
            <span key={f} className="format-chip">.{f.toLowerCase()}</span>
          ))}
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={handleChange}
        accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg,.tiff,.dxf,.dwg"
      />
    </div>
  );
}
