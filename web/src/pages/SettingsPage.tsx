import { useEffect, useState } from "react";
import { getSettings, saveSettings } from "../api/client";
import { useToast } from "../components/shared/Toast";

function KeyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 8a6 6 0 01-7.743 5.743L10 14l-1 1-1 1H6v2H2v-4l4.257-4.257A6 6 0 1118 8zm-6-4a1 1 0 100 2 2 2 0 012 2 1 1 0 102 0 4 4 0 00-4-4z" clipRule="evenodd" />
    </svg>
  );
}

function EyeIcon({ show }: { show: boolean }) {
  if (show) {
    return (
      <svg width="15" height="15" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
      </svg>
    );
  }
  return (
    <svg width="15" height="15" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clipRule="evenodd" />
      <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.064 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  );
}

interface ApiKeyFieldProps {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  isSet: boolean;
}

function ApiKeyField({ label, hint, value, onChange, isSet }: ApiKeyFieldProps) {
  const [show, setShow] = useState(false);

  return (
    <div className="settings-key-card">
      <div className="settings-key-header">
        <div>
          <div className="settings-key-label">{label}</div>
          <div className="settings-key-hint">{hint}</div>
        </div>
        {isSet && (
          <span className="settings-key-status">
            <CheckIcon /> Saved
          </span>
        )}
      </div>
      <div className="settings-key-input-wrap">
        <input
          type={show ? "text" : "password"}
          className="form-input settings-key-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={isSet ? "••••••••••••••••••••••••• (saved)" : "Paste your API key here"}
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="button"
          className="settings-key-toggle"
          onClick={() => setShow((s) => !s)}
          title={show ? "Hide key" : "Show key"}
        >
          <EyeIcon show={show} />
        </button>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiIsSet, setOpenaiIsSet] = useState(false);
  const [anthropicIsSet, setAnthropicIsSet] = useState(false);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    getSettings()
      .then((s) => {
        if (s.openai_api_key) {
          setOpenaiKey(s.openai_api_key);
          setOpenaiIsSet(true);
        }
        if (s.anthropic_api_key) {
          setAnthropicKey(s.anthropic_api_key);
          setAnthropicIsSet(true);
        }
      })
      .catch(() => {});
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await saveSettings({
        openai_api_key: openaiKey || undefined,
        anthropic_api_key: anthropicKey || undefined,
      });
      setOpenaiIsSet(!!updated.openai_api_key);
      setAnthropicIsSet(!!updated.anthropic_api_key);
      toast("Settings saved", "success");
    } catch {
      toast("Failed to save settings", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Settings</h2>
          <p>Configure API keys and application preferences</p>
        </div>
      </div>

      <div className="settings-container">
        <form onSubmit={handleSave}>
          {/* API Keys section */}
          <div className="settings-section">
            <div className="settings-section-header">
              <KeyIcon />
              <div>
                <div className="settings-section-title">API Keys</div>
                <div className="settings-section-desc">
                  Keys are stored locally on your machine in <code>user_settings.json</code> and
                  never transmitted anywhere. At least one key is required to run analysis.
                </div>
              </div>
            </div>

            <div className="settings-keys-list">
              <ApiKeyField
                label="OpenAI API Key"
                hint="Used for document vision analysis and fallback LLM tasks"
                value={openaiKey}
                onChange={(v) => { setOpenaiKey(v); if (v !== openaiKey) setOpenaiIsSet(false); }}
                isSet={openaiIsSet}
              />
              <ApiKeyField
                label="Anthropic API Key"
                hint="Primary LLM for fact extraction, report writing, and analysis"
                value={anthropicKey}
                onChange={(v) => { setAnthropicKey(v); if (v !== anthropicKey) setAnthropicIsSet(false); }}
                isSet={anthropicIsSet}
              />
            </div>
          </div>

          <div className="settings-footer">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <span className="spinner" /> : null}
              Save Settings
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
