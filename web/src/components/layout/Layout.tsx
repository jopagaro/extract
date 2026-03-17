import { Link, useLocation } from "react-router-dom";

interface NavItemProps {
  to: string;
  label: string;
  icon: React.ReactNode;
  exact?: boolean;
}

function NavItem({ to, label, icon, exact = false }: NavItemProps) {
  const { pathname } = useLocation();
  const active = exact ? pathname === to : pathname.startsWith(to);
  return (
    <Link to={to} className={`nav-item ${active ? "active" : ""}`}>
      <span className="nav-icon">{icon}</span>
      {label}
    </Link>
  );
}

function FolderIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path d="M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
    </svg>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Mining Intelligence</h1>
          <p>Project Analysis Platform</p>
        </div>
        <nav className="sidebar-nav">
          <NavItem to="/projects" label="Projects" icon={<FolderIcon />} />
          <NavItem to="/reports" label="Reports" icon={<DocIcon />} />
        </nav>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
