// Extract — Tauri desktop shell
//
// Startup sequence:
//   1. Find a free TCP port (tries 8000, then 8001–8099 until one is free).
//   2. Locate the API server binary (bundled PyInstaller or dev uvicorn).
//   3. Spawn the server on the chosen port; write the port to {data_dir}/api.port.
//   4. Expose a `get_api_port` Tauri command so the web UI can discover the port.
//   5. Give the server ~1.2 s to bind, then open the Tauri window.
//   6. Kill the server cleanly when the window closes.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::api::dialog::message;
use tauri::{Manager, RunEvent, State};

// ── State ────────────────────────────────────────────────────────────────────

struct ApiServer(Mutex<Option<Child>>);
struct ApiPort(u16);

// ── Port discovery ───────────────────────────────────────────────────────────

/// Find a free TCP port, preferring 8000 then 8001–8099.
fn find_free_port() -> u16 {
    let candidates = std::iter::once(8000u16).chain(8001..=8099);
    for port in candidates {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return port;
        }
    }
    // Last resort: let the OS assign any free port
    let listener = TcpListener::bind("127.0.0.1:0").expect("No free port found");
    listener.local_addr().unwrap().port()
}

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
            // Windows venv lives in Scripts/, Unix in bin/
            #[cfg(windows)]
            let python = dir.join(".venv/Scripts/python.exe");
            #[cfg(not(windows))]
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
    port: u16,
) -> Option<Child> {
    std::fs::create_dir_all(data_dir).ok();
    std::fs::create_dir_all(projects_dir).ok();

    // Write the chosen port so the web UI and any external tooling can find it
    let _ = std::fs::write(data_dir.join("api.port"), port.to_string());

    let port_str = port.to_string();

    // ── Production: use the bundled PyInstaller binary ──────────────────────
    if let Some(bin) = find_bundled_binary(resource_dir) {
        let working_dir = bin.parent().unwrap_or(resource_dir).to_path_buf();
        println!("[Extract] Starting bundled API server on port {port}: {}", bin.display());
        return Command::new(&bin)
            .current_dir(&working_dir)
            .env("EXTRACT_DATA_DIR",     data_dir)
            .env("MINING_PROJECTS_ROOT", projects_dir)
            .env("EXTRACT_API_PORT",     &port_str)
            .env("MPLBACKEND",           "Agg")
            .spawn()
            .map_err(|e| eprintln!("[Extract] Failed to start API server: {e}"))
            .ok();
    }

    // ── Development: spawn uvicorn via .venv ────────────────────────────────
    if let Some((root, python)) = find_dev_python() {
        println!("[Extract] Dev mode — spawning uvicorn on port {port}");
        return Command::new(&python)
            .args(["-m", "uvicorn", "api.main:app",
                   "--host", "127.0.0.1", "--port", &port_str])
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

// ── Tauri commands ───────────────────────────────────────────────────────────

/// Called by the React app at startup to discover which port the API is on.
#[tauri::command]
fn get_api_port(port: State<ApiPort>) -> u16 {
    port.0
}

// ── Main ─────────────────────────────────────────────────────────────────────

fn main() {
    let data_dir     = app_data_dir();
    let projects_dir = default_projects_dir();
    let port         = find_free_port();

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_api_port])
        .setup(move |app| {
            let resource_dir = app
                .path_resolver()
                .resource_dir()
                .unwrap_or_else(|| PathBuf::from("."));

            let child = spawn_api_server(&resource_dir, &data_dir, &projects_dir, port);

            if child.is_none() {
                let _ = message(
                    None::<&tauri::Window>,
                    "Extract — API server not running",
                    "The Python API bundle was not found or could not be started. The UI will not load projects.\n\n\
If you are developing: run from the repo with `pnpm --filter desktop dev` (uses .venv + uvicorn).\n\n\
To build the desktop app: from the project root run `./scripts/build_sidecar.sh`, then `pnpm tauri build` from desktop/.",
                );
            }

            // Give the server time to bind before the webview tries to connect
            thread::sleep(Duration::from_millis(1200));

            // If the sidecar didn't start on `port` but something is already
            // serving on 8000 (e.g. a terminal dev uvicorn), use that instead
            // so the UI can reach the API.
            let effective_port = if std::net::TcpStream::connect_timeout(
                &std::net::SocketAddr::from(([127, 0, 0, 1], port)),
                Duration::from_millis(300),
            ).is_ok() {
                port
            } else if port != 8000 && std::net::TcpStream::connect_timeout(
                &std::net::SocketAddr::from(([127, 0, 0, 1], 8000)),
                Duration::from_millis(300),
            ).is_ok() {
                println!("[Extract] Sidecar not responding on {port}, using port 8000");
                let _ = std::fs::write(data_dir.join("api.port"), "8000");
                8000u16
            } else {
                port
            };

            app.manage(ApiServer(Mutex::new(child)));
            app.manage(ApiPort(effective_port));
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
