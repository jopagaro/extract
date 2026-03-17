import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useRef, useState } from "react";
const FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "DXF"];
function UploadIcon() {
    return (_jsxs("svg", { className: "drop-zone-icon", viewBox: "0 0 48 48", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("path", { d: "M24 32V16M24 16l-7 7M24 16l7 7", strokeLinecap: "round", strokeLinejoin: "round" }), _jsx("path", { d: "M8 36a8 8 0 010-16h2.5M40 36a8 8 0 000-16h-2.5M16 24a8 8 0 0116 0", strokeLinecap: "round" })] }));
}
export default function DropZone({ onFiles, disabled = false }) {
    const [dragOver, setDragOver] = useState(false);
    const inputRef = useRef(null);
    function handleDrop(e) {
        e.preventDefault();
        setDragOver(false);
        if (disabled)
            return;
        const files = Array.from(e.dataTransfer.files);
        if (files.length)
            onFiles(files);
    }
    function handleChange(e) {
        const files = Array.from(e.target.files ?? []);
        if (files.length)
            onFiles(files);
        e.target.value = "";
    }
    return (_jsxs("div", { className: `drop-zone ${dragOver ? "drag-over" : ""}`, onDragOver: (e) => { e.preventDefault(); setDragOver(true); }, onDragLeave: () => setDragOver(false), onDrop: handleDrop, onClick: () => !disabled && inputRef.current?.click(), style: { opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }, children: [_jsx(UploadIcon, {}), _jsx("div", { className: "drop-zone-text", children: "Drop files here or click to browse" }), _jsx("div", { className: "drop-zone-sub", children: "Upload all documents related to this project \u2014 technical reports, drill data, financial models" }), _jsx("div", { className: "drop-zone-formats", children: FORMATS.map((f) => (_jsxs("span", { className: "format-chip", children: [".", f.toLowerCase()] }, f))) }), _jsx("input", { ref: inputRef, type: "file", multiple: true, style: { display: "none" }, onChange: handleChange, accept: ".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg,.tiff,.dxf,.dwg" })] }));
}
