import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import { ToastProvider } from "./components/shared/Toast";
import ComparisonPage from "./pages/ComparisonPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import ReportPage from "./pages/ReportPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <ToastProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/report/:runId" element={<ReportPage />} />
          <Route path="/projects/:projectId/compare" element={<ComparisonPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/reports" element={<Navigate to="/projects" replace />} />
        </Routes>
      </Layout>
    </ToastProvider>
  );
}
