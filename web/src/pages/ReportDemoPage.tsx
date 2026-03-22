/**
 * Demo report page — renders the full two-layer report layout
 * with realistic mock data so the design can be reviewed without
 * running an analysis. Navigate to /demo to view.
 */
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

// ── Mock data ────────────────────────────────────────────────────────────────

const MOCK_ASSEMBLY = {
  narrative: `Goldstrike North is an advanced-stage gold development project situated in Elko County, Nevada, approximately 45 kilometres north of the town of Elko. The project is wholly owned and operated by Nevado Gold Corp. and is currently at the Preliminary Economic Assessment (PEA) stage, with a NI 43-101-compliant mineral resource estimate completed in February 2024 by SRK Consulting [Source: SRK Resource Estimate 2024.pdf]. The deposit is hosted in a Carlin-type sedimentary sequence with mineralisation controlled by a NW-trending thrust fault system, a structural setting that has historically produced several world-class gold deposits in the region.

The indicated resource of 42.3 million tonnes at 1.84 g/t gold (2.50 Moz) sits within a larger inferred envelope and supports a planned 3.5 Mtpa conventional open-pit and heap-leach operation [Source: PEA Technical Report 2024.pdf]. The grade profile is notably consistent across the deposit — the coefficient of variation on composites is 0.74 — which reduces the scheduling risk typically associated with Carlin-type deposits and supports the relatively stable annual production profile modelled in the PEA. Metallurgical test work returned heap-leach recoveries of 78–82%, in line with comparable Nevada operations, though the assumed 79% base-case recovery represents a modest risk relative to the upper end of that range [Source: Metallurgy Report Q3 2023.pdf].

The financial model, computed from extracted project parameters at an 8% real discount rate, returns an after-tax NPV of $342 million and an IRR of 22.4%, against a base-case gold price of $1,950 per troy ounce [Source: PEA Technical Report 2024.pdf]. The initial capital requirement of $218 million is well-supported by the project's relatively simple processing flowsheet and the availability of established heap-leach contractors in the Nevada market. All-In Sustaining Costs of $1,045 per ounce place Goldstrike North comfortably in the second quartile of the global gold cost curve, providing meaningful downside protection. At a $1,600/oz gold price — a stress test of approximately -18% — the project still generates a positive NPV of approximately $88 million, demonstrating a reasonable margin of safety.

The principal risk to the project's economic case is permitting. The heap-leach pad footprint intersects with a federally designated sage-grouse habitat management area, which is likely to require additional environmental studies and may extend the permitting timeline by 12–18 months relative to the base case schedule [Source: Environmental Baseline Study 2023.pdf]. A secondary risk is the capital cost estimate, which carries the customary ±35% accuracy range of a PEA and has not been verified by independent cost estimators. On the upside, the strike of mineralisation remains open at depth and to the north-west, and a Phase 2 drill programme targeting a potential underground high-grade core could materially improve project economics at the PFS stage.`,

  analyst_conclusion: `Goldstrike North is a credible development-stage asset with economics that hold up under reasonable stress. The combination of a consistent grade profile, second-quartile all-in costs, and an established jurisdictional setting in Nevada makes this a low-complexity project relative to comparable PEA-stage peers. The permitting overhang is the primary watch item — resolution of the sage-grouse habitat issue will be a material re-rating catalyst. Subject to successful permitting and an updated capital estimate at PFS, the project warrants continued coverage.`,

  key_callouts: [
    { label: "NPV (8% discount, after-tax)", value: "$342M", context: "gold at $1,950/oz base case" },
    { label: "IRR (after-tax)", value: "22.4%", context: "base case, real terms" },
    { label: "AISC", value: "$1,045/oz", context: "all-in sustaining cost" },
    { label: "Payback Period", value: "3.2 yrs", context: "simple payback from first production" },
    { label: "Initial CAPEX", value: "$218M", context: "±35% PEA accuracy" },
    { label: "Indicated Resource", value: "2.50 Moz", context: "42.3 Mt at 1.84 g/t Au" },
    { label: "Mine Life", value: "12 years", context: "based on PEA production schedule" },
    { label: "Annual Production", value: "~210 koz Au", context: "average over life of mine" },
  ],

  study_level: "PEA",
  project_stage: "development",
  disclaimer: null,
  consistency_flags: [],
};

const MOCK_GEOLOGY = {
  deposit_overview: `Goldstrike North is a Carlin-type sedimentary-hosted gold deposit located within the Battle Mountain–Eureka trend, one of Nevada's premier gold-producing corridors. Mineralisation is hosted in silicified and argillised limestone and siltstone of the Roberts Mountains Formation, with gold occurring as submicroscopic inclusions in arsenian pyrite and marcasite. The deposit is structurally controlled by a NW-trending thrust fault system and a series of antithetic normal faults that have created a stacked, tabular mineralised zone with a strike length of approximately 2.1 km and a down-dip extent of up to 450 m [Source: SRK Resource Estimate 2024.pdf].`,

  resource_estimate: `The February 2024 NI 43-101 mineral resource estimate, prepared by SRK Consulting using a 0.30 g/t Au cut-off, reports 42.3 million tonnes at 1.84 g/t gold in the Indicated category (2.50 Moz contained) and a further 18.7 million tonnes at 1.41 g/t in the Inferred category (0.85 Moz). The estimate was constructed from 612 reverse-circulation and core drill holes totalling 94,800 metres [Source: SRK Resource Estimate 2024.pdf]. The coefficient of variation on composites is 0.74, indicating a relatively uniform grade distribution that reduces top-cut sensitivity. No equivalent cut-off resource has been reported — the estimate assumes a conventional open-pit scenario.`,

  geological_risk: `The primary geological risk is the transition from Indicated to Inferred resources in the deeper, north-western portion of the deposit. The inferred ounces are based on wider-spaced drilling (100 m × 100 m versus 50 m × 50 m for the indicated zone) and will require infill drilling to convert to a confidence level suitable for mine planning. A fault offset identified in the southern portion of the deposit in the 2023 programme has not yet been fully characterised; SRK has flagged this as a potential source of grade variability in the first two years of production.`,

  key_metrics: [
    { metric: "Deposit Type", value: "Carlin-type sedimentary-hosted", unit: "", notes: "" },
    { metric: "Strike Length", value: "2.1", unit: "km", notes: "NW-trending" },
    { metric: "Resource Cut-off", value: "0.30", unit: "g/t Au", notes: "open-pit optimised" },
    { metric: "Drill Holes", value: "612", unit: "holes", notes: "94,800m total" },
    { metric: "CV on Composites", value: "0.74", unit: "", notes: "low to moderate variability" },
  ],
};

const MOCK_ECONOMICS = {
  economic_overview: `The PEA financial model was completed by AMC Consultants in March 2024 and evaluated on a 100% equity basis in real 2024 US dollars at an 8% discount rate [Source: PEA Technical Report 2024.pdf]. At a base-case gold price of $1,950/oz, the project generates an after-tax NPV of $342 million and an after-tax IRR of 22.4%, with a simple payback period of 3.2 years from first production. The study evaluates a 3.5 million tonne per annum open-pit heap-leach operation over a 12-year mine life.`,

  capital_costs: `Total initial capital is estimated at $218 million, inclusive of a 15% contingency and owner's costs but excluding working capital and pre-production stripping. The largest cost centres are heap-leach pad and liner ($52 million, 24%), mine mobile equipment ($44 million, 20%), and process plant and infrastructure ($38 million, 17%). Sustaining capital over the mine life is estimated at $68 million, primarily for leach pad lifts and equipment rebuilds, equivalent to approximately $5.7 million per annum [Source: PEA Technical Report 2024.pdf]. A closure provision of $22 million has been included in the model, consistent with Nevada regulatory requirements for heap-leach operations.`,

  operating_costs: `All-In Sustaining Cost is estimated at $1,045 per ounce of gold recovered, comprising cash costs of $875/oz (mining $420/oz, processing $285/oz, G&A $170/oz) plus sustaining capital of $170/oz. The AISC places Goldstrike North in the second quartile of the global gold cost curve as of Q1 2024. The heap-leach process is inherently lower cost than conventional milling but recoveries are correspondingly lower at 79% — a trade-off that has been evaluated against milling scenarios and found to be the value-optimal processing route at the current resource size and grade.`,

  sensitivity_analysis: `The project NPV is most sensitive to gold price, which generates a NPV swing of approximately $115 million per $100/oz change. A 10% reduction in gold price reduces NPV from $342 million to $226 million (IRR 17.1%). A 10% increase in CAPEX reduces NPV by approximately $32 million. A 10% adverse movement in operating costs reduces NPV by approximately $44 million. The sensitivity to gold recovery is meaningful: a 5 percentage-point reduction in recovery (79% to 74%) reduces NPV by approximately $68 million and would bring the IRR below the assumed cost of capital [Source: PEA Technical Report 2024.pdf].`,

  key_metrics: [
    { metric: "NPV (8%)", value: "$342M", unit: "after-tax", notes: "gold at $1,950/oz" },
    { metric: "IRR", value: "22.4%", unit: "after-tax", notes: "real terms" },
    { metric: "Payback", value: "3.2 yrs", unit: "simple", notes: "from first production" },
    { metric: "Gold Price Assumption", value: "$1,950", unit: "USD/oz", notes: "base case" },
    { metric: "Initial CAPEX", value: "$218M", unit: "USD", notes: "±35% accuracy" },
    { metric: "AISC", value: "$1,045", unit: "USD/oz", notes: "all-in sustaining" },
  ],
};

const MOCK_RISKS = {
  permitting_risk: `The most material risk to the project timeline is the regulatory approval process. The heap-leach pad footprint intersects with a BLM-designated sage-grouse Priority Habitat Management Area, which triggers additional NEPA review under the Sage-Grouse Conservation Plan. Management estimates the Environmental Impact Statement process will require 24–30 months; however, legal challenges from environmental groups in analogous Nevada projects have extended EIS timelines by a further 12–18 months in two recent cases. A permitting delay beyond 36 months would push the project financing window into a potentially less favourable interest rate environment and would erode NPV by approximately $18–$24 million per year of delay at the assumed discount rate [Source: Environmental Baseline Study 2023.pdf].`,

  technical_risk: `Metallurgical recovery is the primary technical risk. The assumed 79% heap-leach gold recovery is based on column leach tests conducted on 14 composites, of which four composites from the deeper sulphide-transitional zone returned recoveries of 68–72%. Should the transitional zone represent a higher proportion of mill feed in the early years than modelled, actual recoveries could track below the PEA assumption during the critical payback period. Additionally, the geotechnical characterisation of the heap-leach pad foundation is at a conceptual level only and will require detailed investigation prior to a construction decision.`,

  financial_risk: `Capital cost overruns are a systemic risk at the PEA stage. The ±35% accuracy range on the $218 million initial CAPEX implies a potential upper bound of approximately $295 million at the 90th percentile, which would reduce the base-case NPV by approximately $77 million and compress the IRR to approximately 15%. The project currently has no committed offtake or streaming arrangement, exposing the financing plan to prevailing gold market conditions at the time of the construction decision. Management has indicated preliminary discussions with two streaming counterparties but no terms have been agreed.`,

  mitigants: [
    "Early engagement with BLM and state regulatory bodies is underway; a pre-application meeting was held in Q4 2023",
    "Phase 2 metallurgical test programme targeting transitional zone composites is planned for H1 2025",
    "Geotechnical drilling programme for pad foundation characterisation budgeted for Q3 2024",
    "Open strike extension provides exploration upside that could improve project economics at PFS stage",
  ],
};

const MOCK_DCF = {
  model_ran: true,
  assumptions_notes: "Discount rate 8.0% (extracted from PEA). Tax rate 21.0% (US federal). Metallurgical recovery 79.0% (from test work). Depreciation 10 years straight-line.",
  summary: {
    npv_musd: 342.4,
    irr_percent: 22.4,
    payback_years: 3.2,
    total_initial_capex_musd: 218.0,
    total_sustaining_capex_musd: 68.0,
    total_closure_capex_musd: 22.0,
    average_annual_revenue_musd: 411.0,
    average_annual_opex_musd: 219.5,
    average_aisc: 1045,
    aisc_unit: "USD/oz",
    mine_life_years: 12,
    discount_rate_percent: 8.0,
  },
  cash_flow_table: [
    { year: 0, ore_tonnes: 0, metal_produced: 0, gross_revenue: 0, total_opex: 0, ebitda: 0, capex: 218.0, pre_tax_fcf: -218.0, income_tax: 0, after_tax_fcf: -218.0, pv_cash_flow: -218.0 },
    { year: 1, ore_tonnes: 3500000, metal_produced: 175000, gross_revenue: 341.3, total_opex: 181.2, ebitda: 160.1, capex: 5.8, pre_tax_fcf: 154.3, income_tax: 32.4, after_tax_fcf: 121.9, pv_cash_flow: 113.0 },
    { year: 2, ore_tonnes: 3500000, metal_produced: 210000, gross_revenue: 409.5, total_opex: 219.5, ebitda: 190.0, capex: 5.8, pre_tax_fcf: 184.2, income_tax: 38.7, after_tax_fcf: 145.5, pv_cash_flow: 124.8 },
    { year: 3, ore_tonnes: 3500000, metal_produced: 218000, gross_revenue: 425.1, total_opex: 221.8, ebitda: 203.3, capex: 5.8, pre_tax_fcf: 197.5, income_tax: 41.5, after_tax_fcf: 156.0, pv_cash_flow: 123.9 },
    { year: 4, ore_tonnes: 3500000, metal_produced: 215000, gross_revenue: 419.3, total_opex: 220.5, ebitda: 198.8, capex: 5.8, pre_tax_fcf: 193.0, income_tax: 40.5, after_tax_fcf: 152.5, pv_cash_flow: 112.1 },
    { year: 5, ore_tonnes: 3500000, metal_produced: 212000, gross_revenue: 413.4, total_opex: 219.3, ebitda: 194.1, capex: 5.8, pre_tax_fcf: 188.3, income_tax: 39.5, after_tax_fcf: 148.8, pv_cash_flow: 101.3 },
    { year: 6, ore_tonnes: 3500000, metal_produced: 208000, gross_revenue: 405.6, total_opex: 218.0, ebitda: 187.6, capex: 5.8, pre_tax_fcf: 181.8, income_tax: 38.2, after_tax_fcf: 143.6, pv_cash_flow: 90.5 },
    { year: 12, ore_tonnes: 2100000, metal_produced: 95000, gross_revenue: 185.3, total_opex: 138.2, ebitda: 47.1, capex: 22.0, pre_tax_fcf: 25.1, income_tax: 5.3, after_tax_fcf: 19.8, pv_cash_flow: 7.9 },
  ],
  sensitivity: {
    base_npv_musd: 342.4,
    base_irr_percent: 22.4,
    points: [
      { axis: "commodity_price", change_percent: -20, npv_musd: 88.2, irr_percent: 10.1 },
      { axis: "commodity_price", change_percent: -10, npv_musd: 215.3, irr_percent: 16.4 },
      { axis: "commodity_price", change_percent: 10, npv_musd: 469.5, irr_percent: 28.2 },
      { axis: "commodity_price", change_percent: 20, npv_musd: 596.6, irr_percent: 33.8 },
      { axis: "capex", change_percent: -10, npv_musd: 374.0, irr_percent: 25.6 },
      { axis: "capex", change_percent: 10, npv_musd: 310.8, irr_percent: 19.5 },
      { axis: "capex", change_percent: 20, npv_musd: 279.2, irr_percent: 17.1 },
      { axis: "opex", change_percent: -10, npv_musd: 386.4, irr_percent: 24.8 },
      { axis: "opex", change_percent: 10, npv_musd: 298.4, irr_percent: 20.1 },
    ],
  },
};

const MOCK_SOURCES = {
  generated_at: new Date().toISOString(),
  run_id: "demo_run",
  source_files: [
    "PEA Technical Report 2024.pdf",
    "SRK Resource Estimate 2024.pdf",
    "Metallurgy Report Q3 2023.pdf",
    "Environmental Baseline Study 2023.pdf",
    "Geotechnical Assessment 2023.pdf",
    "Corporate Presentation Q1 2024.pdf",
    "Financial Model v3.2.xlsx",
  ],
  file_count: 7,
  notice: "This is a demonstration report generated with mock data for design review purposes. It does not represent a real project or real analysis.",
};

// ── Shared sub-components (mirrors ReportPage) ───────────────────────────────

function KeyCallouts({ callouts }: { callouts: { label: string; value: string; context?: string }[] }) {
  return (
    <div className="report-callouts-grid">
      {callouts.map((c, i) => (
        <div key={i} className="report-callout-card">
          <div className="report-callout-value">{c.value}</div>
          <div className="report-callout-label">{c.label}</div>
          {c.context && <div className="report-callout-context">{c.context}</div>}
        </div>
      ))}
    </div>
  );
}

function DataTable({ items }: { items: Record<string, unknown>[] }) {
  if (!items.length) return null;
  const cols = Object.keys(items[0]);
  return (
    <div style={{ overflowX: "auto", marginTop: 16 }}>
      <table className="report-table">
        <thead>
          <tr>{cols.map((c) => <th key={c}>{c.replace(/_/g, " ")}</th>)}</tr>
        </thead>
        <tbody>
          {items.map((row, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c}>{row[c] === null || row[c] === undefined ? "—" : String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectionBody({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined);
  const prose = entries.filter(([, v]) => typeof v === "string" && (v as string).length > 60);
  const lists = entries.filter(([, v]) => Array.isArray(v));
  const scalars = entries.filter(([k]) => !prose.find(([p]) => p === k) && !lists.find(([l]) => l === k));
  const single = prose.length === 1 && lists.length === 0 && scalars.length === 0;

  return (
    <div className="report-specialist-body">
      {prose.map(([k, v]) => (
        <div key={k} className="report-prose-para">
          {!single && <div className="report-para-label">{k.replace(/_/g, " ")}</div>}
          <p>{String(v)}</p>
        </div>
      ))}
      {lists.map(([k, v]) => {
        const items = v as unknown[];
        if (!items.length) return null;
        const isObj = typeof items[0] === "object" && items[0] !== null;
        return (
          <div key={k} style={{ marginTop: 20 }}>
            <div className="report-sub-label">{k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</div>
            {isObj
              ? <DataTable items={items as Record<string, unknown>[]} />
              : <ul className="report-bullet-list">{items.map((item, i) => (
                  <li key={i}><span className="report-bullet">—</span><span>{String(item)}</span></li>
                ))}</ul>
            }
          </div>
        );
      })}
      {scalars.length > 0 && (
        <div className="report-scalar-row">
          {scalars.map(([k, v]) => (
            <div key={k} className="report-scalar-chip">
              <span className="report-scalar-label">{k.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
              <span className="report-scalar-value">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── TOC ──────────────────────────────────────────────────────────────────────

const TOC_ITEMS = [
  { key: "narrative", label: "Analyst Narrative" },
  { key: "geology", label: "Geology & Resources", num: "1" },
  { key: "economics", label: "Economics & Finance", num: "2" },
  { key: "risks", label: "Risks & Uncertainties", num: "3" },
  { key: "dcf", label: "DCF Financial Model", num: "4" },
  { key: "sources", label: "Appendix A — Sources" },
];

// ── Demo Page ────────────────────────────────────────────────────────────────

export default function ReportDemoPage() {
  const [showCashFlow, setShowCashFlow] = useState(false);
  const [activeSection, setActiveSection] = useState("narrative");
  const refs = useRef<Record<string, HTMLDivElement | null>>({});

  const scrollTo = (key: string) => {
    refs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveSection(key);
  };

  const generatedAt = new Date().toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });

  return (
    <div className="report-page-layout">
      {/* TOC */}
      <aside className="report-toc-aside">
        <nav className="report-toc">
          <div className="report-toc-label">Contents</div>
          {TOC_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`report-toc-item${activeSection === item.key ? " active" : ""}`}
              onClick={() => scrollTo(item.key)}
            >
              {item.num && <span className="report-toc-num">{item.num}</span>}
              <span>{item.label}</span>
            </button>
          ))}
          <div style={{ marginTop: 20, padding: "0 8px" }}>
            <Link to="/projects" style={{ fontSize: 11.5, color: "var(--r-ink-4)", textDecoration: "none" }}>
              ← Back to projects
            </Link>
          </div>
        </nav>
      </aside>

      {/* Main */}
      <main className="report-main">

        {/* Cover */}
        <div className="report-cover">
          <div className="report-cover-eyebrow">Extract — Technical Analysis Report · Demo</div>
          <div className="report-cover-title">Goldstrike North Gold Project</div>
          <div className="report-cover-subtitle">PEA · Development Stage · Elko County, Nevada, USA</div>
          <div className="report-cover-meta">
            {[
              ["Report Date", generatedAt],
              ["Study Level", "Preliminary Economic Assessment"],
              ["Operator", "Nevado Gold Corp."],
              ["Classification", "Internal — Confidential"],
              ["Prepared By", "Extract AI"],
            ].map(([label, value]) => (
              <div key={label} className="report-cover-meta-item">
                <div className="report-cover-meta-label">{label}</div>
                <div className="report-cover-meta-value">{value}</div>
              </div>
            ))}
          </div>
          <div className="report-disclaimer">
            This is a demonstration report using synthetic data. It does not represent a real project,
            real company, or real analysis. This report does not constitute investment advice.
          </div>
          <div className="report-export-row">
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.38)" }}>
              4 sections · {MOCK_SOURCES.file_count} source documents · Demo mode
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-primary btn-sm" disabled style={{ opacity: 0.5 }}>PDF</button>
              <button className="btn btn-secondary btn-sm" disabled style={{ opacity: 0.5 }}>Markdown</button>
            </div>
          </div>
        </div>

        {/* Layer 1 — Narrative */}
        <div
          ref={(el) => { refs.current["narrative"] = el; }}
          id="narrative"
          className="report-narrative-wrapper"
        >
          <div className="report-narrative-section">
            <KeyCallouts callouts={MOCK_ASSEMBLY.key_callouts} />

            <div className="report-narrative-body">
              {MOCK_ASSEMBLY.narrative.split(/\n\n+/).map((para, i) => (
                <p key={i} className="report-narrative-para">{para}</p>
              ))}
            </div>

            <div className="report-narrative-conclusion">
              <p>{MOCK_ASSEMBLY.analyst_conclusion}</p>
            </div>
          </div>
        </div>

        {/* Layer 2 header */}
        <div className="report-detail-label">Detailed Analysis</div>

        {/* Geology */}
        <div ref={(el) => { refs.current["geology"] = el; }} id="geology" className="report-section">
          <div className="report-section-header">
            <div className="report-section-heading">
              <span className="report-section-number">1</span>
              <div>
                <div className="report-section-title">Geology &amp; Resources</div>
                <div className="report-section-subtitle">Deposit geology and mineral resource assessment</div>
              </div>
            </div>
          </div>
          <SectionBody data={MOCK_GEOLOGY as any} />
        </div>

        {/* Economics */}
        <div ref={(el) => { refs.current["economics"] = el; }} id="economics" className="report-section">
          <div className="report-section-header">
            <div className="report-section-heading">
              <span className="report-section-number">2</span>
              <div>
                <div className="report-section-title">Economics &amp; Financial Analysis</div>
                <div className="report-section-subtitle">Capital costs, operating costs, and financial projections</div>
              </div>
            </div>
          </div>
          <SectionBody data={MOCK_ECONOMICS as any} />
        </div>

        {/* Risks */}
        <div ref={(el) => { refs.current["risks"] = el; }} id="risks" className="report-section">
          <div className="report-section-header">
            <div className="report-section-heading">
              <span className="report-section-number">3</span>
              <div>
                <div className="report-section-title">Risks &amp; Uncertainties</div>
                <div className="report-section-subtitle">Material risks and mitigating factors</div>
              </div>
            </div>
          </div>
          <SectionBody data={MOCK_RISKS as any} />
        </div>

        {/* DCF Model */}
        <div ref={(el) => { refs.current["dcf"] = el; }} id="dcf" className="report-section">
          <div className="report-section-header">
            <div className="report-section-heading">
              <span className="report-section-number">4</span>
              <div>
                <div className="report-section-title">DCF Financial Model</div>
                <div className="report-section-subtitle">Computed discounted cash flow analysis</div>
              </div>
            </div>
          </div>
          <div className="report-specialist-body">
            <div className="report-dcf-notes">
              <strong>Model assumptions:</strong> {MOCK_DCF.assumptions_notes}
            </div>

            <div className="report-sub-label">Valuation Summary</div>
            <div className="report-scalar-row" style={{ marginTop: 8 }}>
              {[
                ["NPV (8%)", "$342.4M"],
                ["IRR", "22.4%"],
                ["Payback", "3.2 yrs"],
                ["Initial CAPEX", "$218.0M"],
                ["Sustaining CAPEX", "$68.0M"],
                ["Closure Provision", "$22.0M"],
                ["Avg. Annual Revenue", "$411.0M"],
                ["AISC", "$1,045/oz"],
                ["Mine Life", "12 yrs"],
              ].map(([label, value]) => (
                <div key={label} className="report-scalar-chip">
                  <span className="report-scalar-label">{label}</span>
                  <span className="report-scalar-value">{value}</span>
                </div>
              ))}
            </div>

            <div className="report-sub-label" style={{ marginTop: 28 }}>Sensitivity to Gold Price &amp; CAPEX</div>
            <DataTable
              items={MOCK_DCF.sensitivity.points.map((p) => ({
                variable: p.axis.replace(/_/g, " "),
                "change (%)": `${p.change_percent > 0 ? "+" : ""}${p.change_percent}%`,
                "NPV (M USD)": p.npv_musd,
                "IRR (%)": p.irr_percent ?? "—",
              }))}
            />

            <div style={{ marginTop: 24 }}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ marginBottom: 12 }}
                onClick={() => setShowCashFlow((v) => !v)}
              >
                {showCashFlow ? "Hide" : "Show"} annual cash flow table
              </button>
              {showCashFlow && (
                <DataTable
                  items={MOCK_DCF.cash_flow_table.map((r) => ({
                    year: r.year,
                    "ore (Mt)": r.ore_tonnes ? (r.ore_tonnes / 1e6).toFixed(1) : "—",
                    "metal (koz)": r.metal_produced ? (r.metal_produced / 1000).toFixed(0) : "—",
                    "revenue ($M)": r.gross_revenue,
                    "opex ($M)": r.total_opex,
                    "capex ($M)": r.capex,
                    "after-tax FCF ($M)": r.after_tax_fcf,
                    "PV ($M)": r.pv_cash_flow,
                  }))}
                />
              )}
            </div>
          </div>
        </div>

        {/* Appendix */}
        <div className="report-detail-label">Appendix</div>
        <div ref={(el) => { refs.current["sources"] = el; }} id="sources" className="report-section report-section--appendix">
          <div className="report-section-header">
            <div className="report-section-title">Appendix A — Source Documents</div>
            <div className="report-section-subtitle">All documents used in this analysis</div>
          </div>
          <div className="report-specialist-body">
            <div className="report-notice">{MOCK_SOURCES.notice}</div>
            <div className="report-sub-label">Source Documents ({MOCK_SOURCES.file_count})</div>
            <div className="report-file-list">
              {MOCK_SOURCES.source_files.map((f, i) => (
                <div key={i} className="report-file-row">
                  <div className="report-file-check">✓</div>
                  {f}
                </div>
              ))}
            </div>
            <div style={{ fontSize: 12, color: "var(--r-ink-4)", marginTop: 16 }}>
              Generated: {new Date(MOCK_SOURCES.generated_at).toLocaleString()}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
