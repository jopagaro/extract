import { useState } from "react";

// ---------------------------------------------------------------------------
// Unit conversion tables (client-side, no network needed)
// ---------------------------------------------------------------------------

type ConvUnit = { label: string; toBase: number };

type ConvCategory = {
  label: string;
  baseUnit: string;
  units: ConvUnit[];
  description: string;
};

const CATEGORIES: ConvCategory[] = [
  {
    label: "Gold Grade",
    baseUnit: "g/t",
    description: "Grade conversion for gold deposits",
    units: [
      { label: "g/t (grams per tonne)", toBase: 1 },
      { label: "oz/t (troy oz per tonne)", toBase: 31.1035 },
      { label: "ppm (same as g/t)", toBase: 1 },
      { label: "ppb (parts per billion)", toBase: 0.001 },
    ],
  },
  {
    label: "Gold Mass",
    baseUnit: "troy oz",
    description: "Gold quantity conversion",
    units: [
      { label: "troy oz", toBase: 1 },
      { label: "grams", toBase: 1 / 31.1035 },
      { label: "kilograms", toBase: 1000 / 31.1035 },
      { label: "Moz (million troy oz)", toBase: 1_000_000 },
    ],
  },
  {
    label: "Copper Grade",
    baseUnit: "% Cu",
    description: "Grade conversion for copper deposits",
    units: [
      { label: "% Cu (percent copper)", toBase: 1 },
      { label: "kg/t (kilograms per tonne)", toBase: 0.1 },
      { label: "lb/t (pounds per tonne)", toBase: 1 / 22.0462 },
      { label: "g/t (grams per tonne)", toBase: 0.0001 },
    ],
  },
  {
    label: "Copper / Base Metal Mass",
    baseUnit: "kt",
    description: "Contained metal quantity for base metals",
    units: [
      { label: "kt (thousand tonnes)", toBase: 1 },
      { label: "Mt (million tonnes)", toBase: 1000 },
      { label: "t (tonnes)", toBase: 0.001 },
      { label: "Mlb (million pounds)", toBase: 0.453592 },
      { label: "lb (pounds)", toBase: 0.000000453592 },
    ],
  },
  {
    label: "Rock / Ore Mass",
    baseUnit: "t (metric)",
    description: "Tonne and ton conversions",
    units: [
      { label: "t (metric tonne)", toBase: 1 },
      { label: "kt (thousand tonnes)", toBase: 1000 },
      { label: "Mt (million tonnes)", toBase: 1_000_000 },
      { label: "short ton (US)", toBase: 0.907185 },
      { label: "long ton (UK)", toBase: 1.016047 },
    ],
  },
  {
    label: "Cost per Oz",
    baseUnit: "USD/oz",
    description: "Gold operating cost unit conversions",
    units: [
      { label: "USD/oz (per troy oz)", toBase: 1 },
      { label: "USD/g (per gram)", toBase: 31.1035 },
      { label: "CAD/oz (at 0.74 FX)", toBase: 0.74 },
      { label: "AUD/oz (at 0.65 FX)", toBase: 0.65 },
    ],
  },
  {
    label: "Cost per Tonne",
    baseUnit: "USD/t",
    description: "Operating cost per tonne of material",
    units: [
      { label: "USD/t (per metric tonne)", toBase: 1 },
      { label: "USD/short ton", toBase: 1.10231 },
      { label: "USD/lb", toBase: 2204.62 },
      { label: "CAD/t (at 0.74 FX)", toBase: 0.74 },
    ],
  },
  {
    label: "Currency Scale",
    baseUnit: "USD",
    description: "Million / thousand / unit conversions",
    units: [
      { label: "USD (dollars)", toBase: 1 },
      { label: "k USD (thousands)", toBase: 1000 },
      { label: "M USD (millions)", toBase: 1_000_000 },
      { label: "B USD (billions)", toBase: 1_000_000_000 },
    ],
  },
];

// ---------------------------------------------------------------------------
// Contained metal calculator
// ---------------------------------------------------------------------------

function calcContainedMoz(tonnageMt: number, gradeGt: number): number {
  // (Mt × 1,000,000 t/Mt × grade g/t) / 31.1035 g/oz / 1,000,000 = Moz
  return (tonnageMt * 1_000_000 * gradeGt) / 31.1035 / 1_000_000;
}

function calcContainedKt(tonnageMt: number, gradePct: number): number {
  // Mt × grade% × 10 kg/t / 1000 kg/t = kt
  return tonnageMt * gradePct * 10;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type Tab = "converter" | "calculator";

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("converter");

  // Converter state
  const [catIdx, setCatIdx] = useState(0);
  const [fromIdx, setFromIdx] = useState(0);
  const [toIdx, setToIdx] = useState(1);
  const [inputVal, setInputVal] = useState("");

  // Calculator state
  const [calcMode, setCalcMode] = useState<"gold" | "copper">("gold");
  const [tonnage, setTonnage] = useState("");
  const [grade, setGrade] = useState("");

  const cat = CATEGORIES[catIdx];
  const fromUnit = cat.units[fromIdx];
  const toUnit = cat.units[toIdx];

  function convert(): string {
    const v = parseFloat(inputVal);
    if (!isFinite(v)) return "—";
    // Convert to base then to target
    const baseVal = v * fromUnit.toBase;
    const result = baseVal / toUnit.toBase;
    // Smart formatting
    if (Math.abs(result) >= 1e9) return result.toExponential(4);
    if (Math.abs(result) >= 1000) return result.toLocaleString(undefined, { maximumFractionDigits: 4 });
    if (Math.abs(result) < 0.00001 && result !== 0) return result.toExponential(4);
    return result.toPrecision(6).replace(/\.?0+$/, "");
  }

  function switchUnits() {
    const tmp = fromIdx;
    setFromIdx(toIdx);
    setToIdx(tmp);
  }

  function onCatChange(idx: number) {
    setCatIdx(idx);
    setFromIdx(0);
    setToIdx(Math.min(1, CATEGORIES[idx].units.length - 1));
    setInputVal("");
  }

  const t = parseFloat(tonnage);
  const g = parseFloat(grade);
  const calcValid = isFinite(t) && t > 0 && isFinite(g) && g > 0;
  const goldMoz = calcValid ? calcContainedMoz(t, g) : null;
  const copperKt = calcValid ? calcContainedKt(t, g) : null;

  return (
    <>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <div>
          <h2>Tools</h2>
          <p>Unit converter and contained metal calculator for mining analysis</p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="tabs" style={{ marginBottom: 28 }}>
        <button className={`tab ${tab === "converter" ? "active" : ""}`} onClick={() => setTab("converter")}>
          Unit Converter
        </button>
        <button className={`tab ${tab === "calculator" ? "active" : ""}`} onClick={() => setTab("calculator")}>
          Contained Metal Calculator
        </button>
      </div>

      {/* ── Unit Converter ─────────────────────────────────────────────────── */}
      {tab === "converter" && (
        <div style={{ maxWidth: 640 }}>
          {/* Category selector */}
          <div className="card" style={{ padding: "18px 20px", marginBottom: 20 }}>
            <div className="form-label" style={{ marginBottom: 10 }}>Category</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {CATEGORIES.map((c, i) => (
                <button
                  key={c.label}
                  onClick={() => onCatChange(i)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: `1.5px solid ${catIdx === i ? "var(--accent)" : "var(--border)"}`,
                    background: catIdx === i ? "rgba(44,74,62,0.07)" : "transparent",
                    color: catIdx === i ? "var(--accent)" : "var(--text-secondary)",
                    fontSize: 12,
                    fontWeight: catIdx === i ? 600 : 400,
                    cursor: "pointer",
                  }}
                >
                  {c.label}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 10 }}>
              {cat.description}
            </div>
          </div>

          {/* Converter UI */}
          <div className="card" style={{ padding: "24px 24px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 12, alignItems: "end", marginBottom: 20 }}>
              {/* From */}
              <div>
                <label className="form-label">From</label>
                <select className="form-input" value={fromIdx}
                  onChange={(e) => { setFromIdx(parseInt(e.target.value)); setInputVal(""); }}>
                  {cat.units.map((u, i) => (
                    <option key={u.label} value={i}>{u.label}</option>
                  ))}
                </select>
              </div>

              {/* Swap button */}
              <button
                onClick={switchUnits}
                style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  border: "1.5px solid var(--border)",
                  background: "transparent",
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                  fontSize: 16,
                  marginBottom: 1,
                }}
                title="Swap units"
              >
                ⇄
              </button>

              {/* To */}
              <div>
                <label className="form-label">To</label>
                <select className="form-input" value={toIdx}
                  onChange={(e) => setToIdx(parseInt(e.target.value))}>
                  {cat.units.map((u, i) => (
                    <option key={u.label} value={i}>{u.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Input + result */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 12, alignItems: "center" }}>
              <div>
                <label className="form-label">Value</label>
                <input
                  className="form-input"
                  type="number"
                  step="any"
                  placeholder="Enter value…"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  style={{ fontSize: 16, fontWeight: 600 }}
                />
              </div>
              <div style={{ paddingTop: 22, color: "var(--text-tertiary)", fontSize: 18 }}>=</div>
              <div>
                <label className="form-label">Result</label>
                <div style={{
                  padding: "9px 12px",
                  borderRadius: 6,
                  border: "1.5px solid var(--border)",
                  fontSize: 16,
                  fontWeight: 700,
                  color: inputVal && convert() !== "—" ? "var(--accent)" : "var(--text-tertiary)",
                  background: "var(--surface-alt, rgba(0,0,0,0.02))",
                  minHeight: 40,
                  display: "flex",
                  alignItems: "center",
                }}>
                  {inputVal ? convert() : "—"}
                </div>
              </div>
            </div>

            {/* Conversion factor */}
            {fromIdx !== toIdx && (
              <div style={{
                marginTop: 18, padding: "10px 14px", borderRadius: 6,
                background: "rgba(44,74,62,0.04)", fontSize: 12,
                color: "var(--text-secondary)", fontFamily: "monospace",
              }}>
                1 {cat.units[fromIdx].label.split(" ")[0]} = {(fromUnit.toBase / toUnit.toBase).toPrecision(6).replace(/\.?0+$/, "")} {cat.units[toIdx].label.split(" ")[0]}
              </div>
            )}
          </div>

          {/* Quick reference */}
          <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: 10 }}>
              Quick Reference
            </div>
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.02)" }}>
                    <th style={{ padding: "8px 14px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)" }}>From</th>
                    <th style={{ padding: "8px 14px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)" }}>To</th>
                    <th style={{ padding: "8px 14px", textAlign: "right", fontWeight: 600, color: "var(--text-secondary)" }}>Factor</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["1 g/t", "oz/t", "÷ 31.1035"],
                    ["1 oz/t", "g/t", "× 31.1035"],
                    ["1 Mt × grade g/t", "Moz", "× grade ÷ 31.1035"],
                    ["1 % Cu", "lb/t", "× 22.046"],
                    ["1 Mlb", "kt", "× 0.4536"],
                    ["1 Mt × grade%", "kt Cu", "× grade × 10"],
                    ["1 $/oz", "$/g", "÷ 31.1035"],
                    ["1 USD/t", "USD/lb", "÷ 2204.62"],
                    ["1 metric tonne", "short ton", "× 1.10231"],
                  ].map(([from, to, factor], i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "7px 14px", color: "var(--text-primary)" }}>{from}</td>
                      <td style={{ padding: "7px 14px", color: "var(--text-secondary)" }}>{to}</td>
                      <td style={{ padding: "7px 14px", textAlign: "right", fontFamily: "monospace", color: "var(--text-primary)" }}>{factor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Contained Metal Calculator ─────────────────────────────────────── */}
      {tab === "calculator" && (
        <div style={{ maxWidth: 560 }}>
          <div className="card" style={{ padding: "24px 24px", marginBottom: 20 }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 18 }}>Contained Metal from Tonnage × Grade</div>

            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
              {(["gold", "copper"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => { setCalcMode(m); setGrade(""); }}
                  style={{
                    padding: "7px 18px",
                    borderRadius: 6,
                    border: `1.5px solid ${calcMode === m ? "var(--accent)" : "var(--border)"}`,
                    background: calcMode === m ? "rgba(44,74,62,0.07)" : "transparent",
                    color: calcMode === m ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight: calcMode === m ? 600 : 400,
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  {m === "gold" ? "Gold (g/t → Moz)" : "Copper (% Cu → kt)"}
                </button>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
              <div>
                <label className="form-label">Tonnage (Mt)</label>
                <input
                  className="form-input"
                  type="number"
                  step="any"
                  min="0"
                  placeholder="e.g. 45.0"
                  value={tonnage}
                  onChange={(e) => setTonnage(e.target.value)}
                  style={{ fontSize: 15 }}
                />
              </div>
              <div>
                <label className="form-label">
                  {calcMode === "gold" ? "Grade (g/t)" : "Grade (% Cu)"}
                </label>
                <input
                  className="form-input"
                  type="number"
                  step="any"
                  min="0"
                  placeholder={calcMode === "gold" ? "e.g. 1.24" : "e.g. 0.45"}
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                  style={{ fontSize: 15 }}
                />
              </div>
            </div>

            {/* Result */}
            <div style={{
              padding: "20px 24px",
              borderRadius: 8,
              background: calcValid
                ? "rgba(44,74,62,0.06)"
                : "rgba(0,0,0,0.02)",
              border: `1.5px solid ${calcValid ? "rgba(44,74,62,0.2)" : "var(--border)"}`,
              textAlign: "center",
            }}>
              {calcValid ? (
                <>
                  {calcMode === "gold" && goldMoz != null && (
                    <>
                      <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent)", marginBottom: 4 }}>
                        {goldMoz.toFixed(3)} Moz
                      </div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        {t.toLocaleString()} Mt × {g} g/t ÷ 31.1035 = <strong>{goldMoz.toFixed(3)} Moz Au</strong>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 8 }}>
                        = {(goldMoz * 31_103.5).toFixed(0)} kg &nbsp;·&nbsp; {(goldMoz * 1_000_000).toLocaleString(undefined, { maximumFractionDigits: 0 })} oz
                      </div>
                    </>
                  )}
                  {calcMode === "copper" && copperKt != null && (
                    <>
                      <div style={{ fontSize: 32, fontWeight: 800, color: "var(--accent)", marginBottom: 4 }}>
                        {copperKt.toFixed(1)} kt Cu
                      </div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        {t.toLocaleString()} Mt × {g}% × 10 = <strong>{copperKt.toFixed(1)} kt Cu</strong>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 8 }}>
                        = {(copperKt / 1000).toFixed(3)} Mt &nbsp;·&nbsp; {(copperKt * 2.20462).toFixed(0)} Mlb &nbsp;·&nbsp; {(copperKt * 1000).toLocaleString()} t
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div style={{ color: "var(--text-tertiary)", fontSize: 14 }}>
                  Enter tonnage and grade above
                </div>
              )}
            </div>
          </div>

          {/* Formula card */}
          <div className="card" style={{ padding: "16px 20px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-tertiary)", marginBottom: 12 }}>
              Formulas
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13, fontFamily: "monospace" }}>
              <div>
                <div style={{ color: "var(--text-tertiary)", fontSize: 11, fontFamily: "sans-serif", marginBottom: 2 }}>Gold — Moz</div>
                <div>Moz = Tonnage (Mt) × Grade (g/t) ÷ 31.1035</div>
              </div>
              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
                <div style={{ color: "var(--text-tertiary)", fontSize: 11, fontFamily: "sans-serif", marginBottom: 2 }}>Copper — kt</div>
                <div>kt = Tonnage (Mt) × Grade (%) × 10</div>
              </div>
              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 10 }}>
                <div style={{ color: "var(--text-tertiary)", fontSize: 11, fontFamily: "sans-serif", marginBottom: 2 }}>Copper — Mlb</div>
                <div>Mlb = Tonnage (Mt) × Grade (%) × 22.046</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
