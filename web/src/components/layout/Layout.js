import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Link, useLocation } from "react-router-dom";
function NavItem({ to, label, icon, exact = false }) {
    const { pathname } = useLocation();
    const active = exact ? pathname === to : pathname.startsWith(to);
    return (_jsxs(Link, { to: to, className: `nav-item ${active ? "active" : ""}`, children: [_jsx("span", { className: "nav-icon", children: icon }), label] }));
}
function FolderIcon() {
    return (_jsx("svg", { viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { d: "M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" }) }));
}
function DocIcon() {
    return (_jsx("svg", { viewBox: "0 0 20 20", fill: "currentColor", children: _jsx("path", { fillRule: "evenodd", d: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z", clipRule: "evenodd" }) }));
}
export default function Layout({ children }) {
    return (_jsxs("div", { className: "app-layout", children: [_jsxs("aside", { className: "sidebar", children: [_jsxs("div", { className: "sidebar-brand", children: [_jsx("h1", { children: "Mining Intelligence" }), _jsx("p", { children: "Project Analysis Platform" })] }), _jsxs("nav", { className: "sidebar-nav", children: [_jsx(NavItem, { to: "/projects", label: "Projects", icon: _jsx(FolderIcon, {}) }), _jsx(NavItem, { to: "/reports", label: "Reports", icon: _jsx(DocIcon, {}) })] })] }), _jsx("main", { className: "main-content", children: children })] }));
}
