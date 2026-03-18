import { useRef, useState } from "react";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG/JPG", "DXF"];

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

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
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
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
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
