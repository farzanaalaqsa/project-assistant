from __future__ import annotations

from pathlib import Path
from datetime import date

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_data"


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, title)
    y -= 24
    c.setFont("Helvetica", 10)

    for line in lines:
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 10)
        c.drawString(72, y, line[:120])
        y -= 14

    c.save()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # --- PDFs (messy, narrative) ---
    write_pdf(
        OUT / "project_status_report_feb_2026.pdf",
        "Project Status Report — NorthBank LRT Extension (Feb 2026)",
        [
            "Project: NorthBank LRT Extension (NB-LRT-X)",
            "Reporting period: 2026-02-01 to 2026-02-29",
            "Overall health: AMBER (schedule pressure; procurement delays).",
            "",
            "Key milestones (note: some dates pending vendor confirmation):",
            "- M1: Site mobilisation — DONE (2026-01-18)",
            "- M2: Piling works start — DONE (2026-02-10)",
            "- M3: Station A foundations — 70% complete (ETA 2026-03-22)",
            "- M4: Traction power substation tender award — slipped (was 2026-02-20, now ~2026-03-08)",
            "",
            "Budget snapshot:",
            "- Approved Budget (AB): RM 120,000,000",
            "- Forecast at Completion (EAC): RM 126.5m (includes +RM 4.2m steel escalation, +RM 2.3m redesign)",
            "- Actuals to date (as of 2026-02-28): RM 18.7m",
            "",
            "Top risks (see Risk Register for full list):",
            "- R-07: Utility relocation permits delayed; may impact track bed start.",
            "- R-12: Steel price volatility (mitigation: lock-in PO by mid-Mar).",
            "- R-03: Monsoon rainfall; productivity loss.",
            "",
            "Notes / inconsistencies:",
            "- Some subcontractor reports quote amounts in 'MYR' instead of 'RM'.",
            "- Several deliverables missing owners in the action log.",
        ],
    )

    write_pdf(
        OUT / "project_status_report_mar_2026.pdf",
        "Project Status Report — NorthBank LRT Extension (Mar 2026)",
        [
            "Project: NB-LRT-X",
            "Reporting period: 2026-03-01 to 2026-03-31",
            "Overall health: AMBER trending to RED if permits not cleared by 2026-04-10.",
            "",
            "Progress highlights:",
            "- Station A foundations — 95% complete (some rework on pier P-14)",
            "- Piling works — COMPLETE for Station A; Station B started late due to access issues",
            "- Traction power tender — AWARDED 2026-03-12 (vendor: VoltWorks)",
            "",
            "Schedule concerns:",
            "- Critical path now runs through Utility Relocation → Track Bed Prep → Track Install.",
            "- Utility relocation is 3 weeks behind; permits still pending from CityWorks.",
            "",
            "Budget snapshot (from Finance v3):",
            "- AB: RM120m",
            "- EAC: RM127.1m (note: different from Feb report due to updated civils scope)",
            "- Actuals to date (as of 2026-03-31): RM 29.4m",
            "",
            "Key decision required:",
            "- Approve weekend working for utilities team (adds ~RM 0.35m/month).",
        ],
    )

    write_pdf(
        OUT / "risk_workshop_notes.pdf",
        "Risk Workshop Notes — NB-LRT-X (2026-03-18)",
        [
            "Attendees: PM, Planning Lead, QS, Utilities Lead, Safety Officer",
            "",
            "Emerging risks discussed:",
            "- Permit dependency: CityWorks backlog; expect approvals 'early April' (not firm).",
            "- Third-party interface: telecom duct relocation scope unclear (missing drawings).",
            "- Budget sensitivity: overtime for utilities; steel escalation; diesel price.",
            "",
            "Potential mitigations:",
            "- Escalate to municipal steering committee; request fast-track.",
            "- Split workfronts to proceed with non-dependent sections.",
            "- Use provisional sums for telecom interface until drawings received.",
        ],
    )

    # --- CSV / Excel (tabular) ---
    financial = pd.DataFrame(
        [
            {"Cost Code": "CIV-01", "Package": "Civils", "Budget (RM)": "55,000,000", "Actual RM": "14,200,000", "Forecast_RM": "58,300,000"},
            {"Cost Code": "SYS-02", "Package": "Systems", "Budget (RM)": "35,000,000", "Actual RM": "3,900,000", "Forecast_RM": "36,800,000"},
            {"Cost Code": "UTL-03", "Package": "Utilities", "Budget (RM)": "12,000,000", "Actual RM": "6,100,000", "Forecast_RM": "14,100,000"},
            {"Cost Code": "PMO-04", "Package": "PMO & Supervision", "Budget (RM)": "8,000,000", "Actual RM": "2,700,000", "Forecast_RM": "8,400,000"},
            {"Cost Code": "RSV-99", "Package": "Contingency", "Budget (RM)": "10,000,000", "Actual RM": "2,500,000", "Forecast_RM": "9,500,000"},
            # messy row with missing actual
            {"Cost Code": "MISC", "Package": "Misc / Claims", "Budget (RM)": "0", "Actual RM": "", "Forecast_RM": "1,000,000"},
        ]
    )
    financial.to_excel(OUT / "financial_summary.xlsx", index=False, sheet_name="Finance v3")

    risks = pd.DataFrame(
        [
            {"Risk ID": "R-03", "Description": "Monsoon rainfall reduces productivity", "Likelihood": "High", "Impact": "Medium", "Status": "Open", "Owner": "Planning", "Mitigation": "Float reallocation; weather windows"},
            {"Risk ID": "R-07", "Description": "Utility relocation permits delayed by CityWorks", "Likelihood": "High", "Impact": "High", "Status": "Open", "Owner": "Utilities", "Mitigation": "Escalate; fast-track request; weekend works"},
            {"Risk ID": "R-12", "Description": "Steel price volatility / supplier lead time", "Likelihood": "Medium", "Impact": "High", "Status": "Open", "Owner": "QS", "Mitigation": "Lock-in PO; alternate suppliers"},
            # messy: missing owner
            {"Risk ID": "R-15", "Description": "Telecom duct relocation scope unclear (missing drawings)", "Likelihood": "Medium", "Impact": "Medium", "Status": "Open", "Owner": "", "Mitigation": "Provisional sums; request drawings"},
            {"Risk ID": "R-02", "Description": "Safety incident during night works", "Likelihood": "Low", "Impact": "High", "Status": "Mitigating", "Owner": "HSE", "Mitigation": "Permit-to-work; lighting; supervision"},
        ]
    )
    risks.to_csv(OUT / "risk_register.csv", index=False)

    print(f"Wrote sample data to: {OUT}")


if __name__ == "__main__":
    main()

