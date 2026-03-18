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
    <svg className="drop-zone-icon" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M24 32V16M24 16l-7 7M24 16l7 7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M8 36a8 8 0 010-16h2.5M40 36a8 8 0 000-16h-2.5M16 24a8 8 0 0116 0" strokeLinecap="round" />
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
      <UploadIcon />
      <div className="drop-zone-text">Drop files here or click to browse</div>
      <div className="drop-zone-sub">
        Upload all documents related to this project — technical reports, drill data, financial models
      </div>
      <div className="drop-zone-formats">
        {FORMATS.map((f) => (
          <span key={f} className="format-chip">.{f.toLowerCase()}</span>
        ))}
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
