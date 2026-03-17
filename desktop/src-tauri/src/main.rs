// Mining Intelligence Platform — Tauri desktop shell
//
// On startup:
//   1. Locates the Python virtual environment next to the app bundle
//   2. Spawns `uvicorn api.main:app --port 8000` from the platform root
//   3. Opens the React UI in a native macOS window
//
// On window close: kills the uvicorn process cleanly.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::{Manager, RunEvent};

// Shared state — holds the handle to the Python server process
struct ApiServer(Mutex<Option<Child>>);

/// Find the platform root directory.
/// In dev:     two dirs up from the Cargo manifest = mining_intelligence_platform/
/// In release: next to the .app bundle
fn find_platform_root() -> PathBuf {
    // Walk up from the executable looking for pyproject.toml as a marker
    let mut dir = std::env::current_exe()
        .unwrap_or_default()
        .parent()
        .unwrap_or(&PathBuf::from("."))
        .to_path_buf();

    for _ in 0..10 {
        if dir.join("pyproject.toml").exists() {
            return dir;
        }
        match dir.parent() {
            Some(p) => dir = p.to_path_buf(),
            None => break,
        }
    }

    // Fallback: developer is running `cargo tauri dev` from desktop/src-tauri
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()   // desktop/
        .and_then(|p| p.parent()) // mining_intelligence_platform/
        .unwrap_or(&PathBuf::from("."))
        .to_path_buf()
}

/// Resolve the Python executable — prefer the .venv inside the platform root.
fn find_python(platform_root: &PathBuf) -> PathBuf {
    let venv_python = platform_root.join(".venv/bin/python");
    if venv_python.exists() {
        return venv_python;
    }
    // Fallback to system python3
    PathBuf::from("python3")
}

fn spawn_api_server(platform_root: &PathBuf) -> Option<Child> {
    let python = find_python(platform_root);

    // Use python -m uvicorn so we don't need uvicorn on PATH
    let child = Command::new(&python)
        .args(["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"])
        .current_dir(platform_root)
        .spawn();

    match child {
        Ok(c) => {
            println!("[MIP] API server started (pid {})", c.id());
            Some(c)
        }
        Err(e) => {
            eprintln!("[MIP] Failed to start API server: {e}");
            None
        }
    }
}

fn main() {
    let platform_root = find_platform_root();
    println!("[MIP] Platform root: {}", platform_root.display());

    // Start the API server before the Tauri window opens
    let server_child = spawn_api_server(&platform_root);

    // Give uvicorn a moment to bind to the port
    thread::sleep(Duration::from_millis(800));

    tauri::Builder::default()
        .manage(ApiServer(Mutex::new(server_child)))
        .build(tauri::generate_context!())
        .expect("Failed to build Tauri application")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                // Shut down the Python server when the app closes
                let state = app_handle.state::<ApiServer>();
                let child_opt = state.0.lock().ok().and_then(|mut g| g.take());
                if let Some(mut child) = child_opt {
                    println!("[MIP] Shutting down API server…");
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        });
}
