import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import { ToastProvider } from "./components/shared/Toast";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import ReportPage from "./pages/ReportPage";
export default function App() {
    return (_jsx(ToastProvider, { children: _jsx(Layout, { children: _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(Navigate, { to: "/projects", replace: true }) }), _jsx(Route, { path: "/projects", element: _jsx(ProjectsPage, {}) }), _jsx(Route, { path: "/projects/:projectId", element: _jsx(ProjectDetailPage, {}) }), _jsx(Route, { path: "/projects/:projectId/report/:runId", element: _jsx(ReportPage, {}) }), _jsx(Route, { path: "/reports", element: _jsx(Navigate, { to: "/projects", replace: true }) })] }) }) }));
}
