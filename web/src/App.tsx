import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import { ToastProvider } from "./components/shared/Toast";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectsPage from "./pages/ProjectsPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <ToastProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/report/:runId" element={<ReportPage />} />
          <Route path="/reports" element={<Navigate to="/projects" replace />} />
        </Routes>
      </Layout>
    </ToastProvider>
  );
}
