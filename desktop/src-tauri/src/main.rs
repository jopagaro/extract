// Extract — Tauri desktop shell
//
// Startup sequence:
//   1. Locate the API server binary:
//      · In a production bundle: binaries/api-server/api-server inside Resources
//      · In dev: spawn uvicorn via the .venv Python (same as before)
//   2. Set EXTRACT_DATA_DIR and MINING_PROJECTS_ROOT before spawning.
//   3. Give the server ~1.2 s to bind, then open the Tauri window.
//   4. Kill the server cleanly when the window closes.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::{Manager, RunEvent};

// ── State ────────────────────────────────────────────────────────────────────

struct ApiServer(Mutex<Option<Child>>);

// ── Path helpers ─────────────────────────────────────────────────────────────

/// Returns the platform-appropriate app data directory.
/// Mirrors the logic in api_server_entry.py.
fn app_data_dir() -> PathBuf {
    #[cfg(target_os = "macos")]
    {
        dirs_next::home_dir()
            .unwrap_or_default()
            .join("Library/Application Support/com.extract.app")
    }
    #[cfg(target_os = "windows")]
    {
        std::env::var("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs_next::home_dir().unwrap_or_default())
            .join("com.extract.app")
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        dirs_next::home_dir()
            .unwrap_or_default()
            .join(".config/com.extract.app")
    }
}

fn default_projects_dir() -> PathBuf {
    dirs_next::document_dir()
        .unwrap_or_else(|| dirs_next::home_dir().unwrap_or_default())
        .join("Extract Projects")
}

// ── Binary discovery ─────────────────────────────────────────────────────────

/// In a production bundle, Tauri copies the `binaries/api-server/` directory
/// into the app's Resources folder.  Find the executable there.
fn find_bundled_binary(resource_dir: &PathBuf) -> Option<PathBuf> {
    #[cfg(windows)]
    let exe = "api-server.exe";
    #[cfg(not(windows))]
    let exe = "api-server";

    let candidate = resource_dir.join("binaries").join("api-server").join(exe);
    if candidate.exists() {
        Some(candidate)
    } else {
        None
    }
}

/// In dev, locate the project root (has pyproject.toml) and return
/// (project_root, venv_python).
fn find_dev_python() -> Option<(PathBuf, PathBuf)> {
    let mut dir = std::env::current_exe()
        .unwrap_or_default()
        .parent()
        .unwrap_or(&PathBuf::from("."))
        .to_path_buf();

    for _ in 0..14 {
        if dir.join("pyproject.toml").exists() {
            let python = dir.join(".venv/bin/python");
            if python.exists() {
                return Some((dir, python));
            }
        }
        match dir.parent() {
            Some(p) => dir = p.to_path_buf(),
            None => break,
        }
    }
    None
}

// ── Server spawn ─────────────────────────────────────────────────────────────

fn spawn_api_server(
    resource_dir: &PathBuf,
    data_dir: &PathBuf,
    projects_dir: &PathBuf,
) -> Option<Child> {
    std::fs::create_dir_all(data_dir).ok();
    std::fs::create_dir_all(projects_dir).ok();

    // ── Production: use the bundled PyInstaller binary ──────────────────────
    if let Some(bin) = find_bundled_binary(resource_dir) {
        let working_dir = bin.parent().unwrap_or(resource_dir).to_path_buf();
        println!("[Extract] Starting bundled API server: {}", bin.display());
        return Command::new(&bin)
            .current_dir(&working_dir)
            .env("EXTRACT_DATA_DIR",     data_dir)
            .env("MINING_PROJECTS_ROOT", projects_dir)
            .env("MPLBACKEND",           "Agg")
            .spawn()
            .map_err(|e| eprintln!("[Extract] Failed to start API server: {e}"))
            .ok();
    }

    // ── Development: spawn uvicorn via .venv ────────────────────────────────
    if let Some((root, python)) = find_dev_python() {
        println!("[Extract] Dev mode — spawning uvicorn from {}", root.display());
        let port = std::env::var("EXTRACT_API_PORT").unwrap_or_else(|_| "8000".to_string());
        return Command::new(&python)
            .args(["-m", "uvicorn", "api.main:app",
                   "--host", "127.0.0.1", "--port", &port])
            .current_dir(&root)
            .env("EXTRACT_DATA_DIR",     data_dir)
            .env("MINING_PROJECTS_ROOT", projects_dir)
            .env("MPLBACKEND",           "Agg")
            .spawn()
            .map_err(|e| eprintln!("[Extract] Failed to start dev server: {e}"))
            .ok();
    }

    eprintln!("[Extract] Could not locate API server — running without backend.");
    None
}

// ── Main ─────────────────────────────────────────────────────────────────────

fn main() {
    let data_dir     = app_data_dir();
    let projects_dir = default_projects_dir();

    tauri::Builder::default()
        .setup(move |app| {
            let resource_dir = app
                .path_resolver()
                .resource_dir()
                .unwrap_or_else(|| PathBuf::from("."));

            let child = spawn_api_server(&resource_dir, &data_dir, &projects_dir);

            // Give the server time to bind before the webview tries to connect
            thread::sleep(Duration::from_millis(1200));

            app.manage(ApiServer(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Failed to build Tauri application")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                let state = app_handle.state::<ApiServer>();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        println!("[Extract] Shutting down API server…");
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                };
            }
        });
}
