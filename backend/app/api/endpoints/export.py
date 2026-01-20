"""Export API endpoints for CSV, JSON, and PDF reports."""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.simulation import SimulationRun

router = APIRouter()

# Reference to simulation store (imported from simulation endpoint)
from app.api.endpoints.simulation import _simulation_store


@router.get("/{run_id}/csv")
async def export_csv(run_id: UUID) -> StreamingResponse:
    """
    Export simulation results as CSV.

    Returns a CSV file with turbine-level results.
    """
    run = _get_completed_run(run_id)

    # Build CSV content
    lines = [
        "direction_deg,wind_speed_ms,turbine_name,free_stream_power_kw,"
        "wake_affected_power_kw,power_loss_kw,power_loss_percent,"
        "effective_speed_ms,velocity_deficit"
    ]

    if run.results:
        for dir_result in run.results.directional_results:
            for farm_result in dir_result.farm_results:
                for t in farm_result.turbine_results:
                    lines.append(
                        f"{dir_result.direction},{farm_result.wind_speed},"
                        f"{t.turbine_name},{t.free_stream_power:.2f},"
                        f"{t.wake_affected_power:.2f},{t.power_loss:.2f},"
                        f"{t.power_loss_percent:.2f},{t.effective_speed:.2f},"
                        f"{t.combined_velocity_deficit:.4f}"
                    )

    content = "\n".join(lines)
    buffer = io.BytesIO(content.encode())

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=simulation_{run_id}_results.csv"
        },
    )


@router.get("/{run_id}/json")
async def export_json(run_id: UUID) -> StreamingResponse:
    """
    Export simulation results as JSON.

    Returns complete simulation results in JSON format.
    """
    run = _get_completed_run(run_id)

    # Convert to JSON
    export_data = {
        "simulation_id": str(run.id),
        "name": run.name,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "layout": {
            "name": run.layout.name,
            "turbine_count": run.layout.turbine_count,
            "total_rated_power_kw": run.layout.total_rated_power,
            "turbines": [
                {
                    "name": t.name,
                    "latitude": t.latitude,
                    "longitude": t.longitude,
                    "hub_height": t.hub_height,
                    "rotor_diameter": t.rotor_diameter,
                    "rated_power": t.rated_power,
                }
                for t in run.layout.turbines
            ],
        },
        "config": {
            "wake_model": run.config.wake_params.model_type.value,
            "wake_decay_coefficient": run.config.wake_params.wake_decay_coefficient,
            "direction_resolution": run.config.direction_resolution,
        },
    }

    if run.results:
        export_data["results"] = {
            "overall_wake_loss_percent": run.results.overall_wake_loss_percent,
            "worst_direction_deg": run.results.worst_direction,
            "best_direction_deg": run.results.best_direction,
            "computation_time_seconds": run.results.computation_time_seconds,
        }

        if run.results.aep:
            export_data["aep"] = {
                "gross_aep_mwh": run.results.aep.gross_aep_mwh,
                "net_aep_mwh": run.results.aep.net_aep_mwh,
                "wake_loss_mwh": run.results.aep.wake_loss_mwh,
                "wake_loss_percent": run.results.aep.wake_loss_percent,
                "gross_capacity_factor_percent": run.results.aep.gross_capacity_factor,
                "net_capacity_factor_percent": run.results.aep.net_capacity_factor,
            }

    content = json.dumps(export_data, indent=2)
    buffer = io.BytesIO(content.encode())

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=simulation_{run_id}_results.json"
        },
    )


@router.get("/{run_id}/summary")
async def export_summary(run_id: UUID) -> dict[str, Any]:
    """
    Get a summary of simulation results.

    Returns key metrics and statistics.
    """
    run = _get_completed_run(run_id)

    summary: dict[str, Any] = {
        "simulation_id": str(run.id),
        "name": run.name,
        "status": run.status.value,
        "farm": {
            "name": run.layout.name,
            "turbine_count": run.layout.turbine_count,
            "total_rated_power_mw": run.layout.total_rated_power / 1000,
        },
    }

    if run.results:
        summary["wake_loss"] = {
            "overall_percent": round(run.results.overall_wake_loss_percent, 2),
            "worst_direction_deg": run.results.worst_direction,
            "best_direction_deg": run.results.best_direction,
        }

        if run.results.aep:
            summary["aep"] = {
                "gross_mwh": round(run.results.aep.gross_aep_mwh, 1),
                "net_mwh": round(run.results.aep.net_aep_mwh, 1),
                "loss_mwh": round(run.results.aep.wake_loss_mwh, 1),
                "loss_percent": round(run.results.aep.wake_loss_percent, 2),
                "net_capacity_factor_percent": round(
                    run.results.aep.net_capacity_factor, 2
                ),
                "full_load_hours": round(run.results.aep.net_full_load_hours, 0),
            }

    return summary


@router.get("/{run_id}/pdf")
async def export_pdf(run_id: UUID) -> StreamingResponse:
    """
    Export simulation results as PDF report.

    Generates a professional PDF report with layout, charts, and tables.
    """
    run = _get_completed_run(run_id)

    try:
        pdf_buffer = _generate_pdf_report(run)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=simulation_{run_id}_report.pdf"
            },
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF generation requires reportlab. Install with: pip install reportlab",
        )


def _get_completed_run(run_id: UUID) -> SimulationRun:
    """Get a completed simulation run or raise error."""
    if run_id not in _simulation_store:
        raise HTTPException(status_code=404, detail="Simulation not found")

    run = _simulation_store[run_id]

    if run.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not completed. Status: {run.status.value}",
        )

    return run


def _generate_pdf_report(run: SimulationRun) -> io.BytesIO:
    """Generate PDF report for simulation."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor("#1a365d"),
    )
    story.append(Paragraph("Wind Farm Wake Loss Report", title_style))

    # Simulation info
    story.append(Paragraph(f"<b>Simulation:</b> {run.name}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 20))

    # Farm summary
    story.append(Paragraph("Farm Summary", styles["Heading2"]))
    farm_data = [
        ["Parameter", "Value"],
        ["Farm Name", run.layout.name],
        ["Number of Turbines", str(run.layout.turbine_count)],
        ["Total Rated Power", f"{run.layout.total_rated_power / 1000:.1f} MW"],
    ]
    farm_table = Table(farm_data, colWidths=[100*mm, 60*mm])
    farm_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
            ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ])
    )
    story.append(farm_table)
    story.append(Spacer(1, 20))

    # Results
    if run.results:
        story.append(Paragraph("Wake Loss Results", styles["Heading2"]))
        results_data = [
            ["Metric", "Value"],
            [
                "Overall Wake Loss",
                f"{run.results.overall_wake_loss_percent:.2f}%",
            ],
            ["Worst Direction", f"{run.results.worst_direction:.0f}°"],
            ["Best Direction", f"{run.results.best_direction:.0f}°"],
        ]

        if run.results.aep:
            results_data.extend([
                ["Gross AEP", f"{run.results.aep.gross_aep_mwh:,.0f} MWh"],
                ["Net AEP", f"{run.results.aep.net_aep_mwh:,.0f} MWh"],
                ["AEP Loss", f"{run.results.aep.wake_loss_mwh:,.0f} MWh"],
                [
                    "Net Capacity Factor",
                    f"{run.results.aep.net_capacity_factor:.1f}%",
                ],
            ])

        results_table = Table(results_data, colWidths=[100*mm, 60*mm])
        results_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ])
        )
        story.append(results_table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    return buffer
