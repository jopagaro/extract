import { useState } from "react";
import { activateLicense } from "../api/client";

export default function ActivatePage({ onActivated }: { onActivated: () => void }) {
  const [key, setKey]       = useState("");
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handleActivate = async () => {
    const trimmed = key.trim().toUpperCase();
    if (!trimmed) {
      setError("Please enter your license key.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await activateLicense(trimmed);
      if (result.success) {
        onActivated();
      } else {
        setError(result.message || "Invalid license key.");
      }
    } catch (err: any) {
      setError(err.message ?? "Could not reach the activation server. Check your internet connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="activate-page">
      <div className="activate-card">
        {/* Gold top bar */}
        <div className="activate-gold-bar" />

        <div className="activate-inner">
          <div className="activate-eyebrow">Extract</div>
          <h1 className="activate-title">Activate your license</h1>
          <p className="activate-body">
            Enter the license key from your purchase confirmation email.
            An internet connection is required for first-time activation.
          </p>

          <div className="activate-field">
            <input
              className={`activate-input${error ? " activate-input--error" : ""}`}
              type="text"
              placeholder="EXTR-XXXX-XXXX-XXXX-XXXX"
              value={key}
              onChange={(e) => {
                setKey(e.target.value.toUpperCase());
                if (error) setError("");
              }}
              onKeyDown={(e) => e.key === "Enter" && !loading && handleActivate()}
              autoFocus
              spellCheck={false}
              autoCapitalize="characters"
            />
            {error && <div className="activate-error">{error}</div>}
          </div>

          <button
            className="activate-btn"
            onClick={handleActivate}
            disabled={loading}
          >
            {loading ? (
              <span className="spinner" style={{ width: 16, height: 16 }} />
            ) : (
              "Activate"
            )}
          </button>

          <p className="activate-footer">
            Don't have a license?{" "}
            <a
              href="https://yourdomain.com/extract"
              target="_blank"
              rel="noreferrer"
            >
              Purchase Extract →
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
