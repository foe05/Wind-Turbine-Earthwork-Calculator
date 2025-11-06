"""
Report API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
import logging
from pathlib import Path
from datetime import datetime, timedelta
import os

from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.core.generator import ReportGenerator
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["Report"])
settings = get_settings()

# Initialize generator
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
REPORTS_DIR = Path(settings.REPORTS_DIR)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

generator = ReportGenerator(str(TEMPLATES_DIR))


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerateRequest):
    """
    Generate report (HTML or PDF)

    Creates a formatted report from calculation results.
    Supports multiple template types: WKA, Road, Solar, Terrain
    """
    logger.info("=" * 70)
    logger.info(f"Generating {request.format.upper()} report: {request.project_name}")
    logger.info(f"Template: {request.template}")
    logger.info("=" * 70)

    # Prepare template data based on template type
    data = {'project_name': request.project_name}

    if request.template == 'wka':
        # WKA template
        if not request.sites:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="sites data required for WKA template"
            )

        sites_data = [site.dict() for site in request.sites]
        total_sites = len(sites_data)
        total_cut = sum(s['total_cut'] for s in sites_data)
        total_fill = sum(s['total_fill'] for s in sites_data)
        total_cost = sum(s['cost_total'] for s in sites_data)

        data.update({
            'total_sites': total_sites,
            'total_cut': total_cut,
            'total_fill': total_fill,
            'total_cost': total_cost,
            'sites': sites_data
        })

    elif request.template == 'road':
        # Road template
        if not request.road_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="road_data required for Road template"
            )
        data.update(request.road_data.dict())

    elif request.template == 'solar':
        # Solar template
        if not request.solar_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="solar_data required for Solar template"
            )
        data.update(request.solar_data.dict())

    elif request.template == 'terrain':
        # Terrain template
        if not request.terrain_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="terrain_data required for Terrain template"
            )

        # Add human-readable analysis type label
        analysis_type_labels = {
            'cut_fill_balance': 'Aushub/Auftrag Balance-Optimierung',
            'volume_calculation': 'Volumenberechnung',
            'slope_analysis': 'Hangneigung-Analyse',
            'contour_generation': 'Höhenlinien-Generierung'
        }

        terrain_dict = request.terrain_data.dict()
        if 'analysis_type_label' not in terrain_dict or not terrain_dict['analysis_type_label']:
            terrain_dict['analysis_type_label'] = analysis_type_labels.get(
                terrain_dict['analysis_type'],
                terrain_dict['analysis_type']
            )

        data.update(terrain_dict)

    # Generate report
    try:
        file_path, report_id = generator.generate_report(
            template=request.template,
            data=data,
            output_format=request.format,
            reports_dir=REPORTS_DIR
        )

        # Get file size
        file_size = file_path.stat().st_size

        # Generate download URL
        filename = file_path.name
        download_url = f"/report/download/{report_id}/{filename}"

        # Calculate expiration
        generated_at = datetime.utcnow()
        expires_at = generated_at + timedelta(days=settings.REPORT_EXPIRATION_DAYS)

        logger.info(f"✓ Report generated: {report_id}")
        logger.info(f"  File: {file_path}")
        logger.info(f"  Size: {file_size / 1024:.1f} KB")
        logger.info("=" * 70 + "\n")

        return ReportResponse(
            report_id=report_id,
            format=request.format,
            download_url=download_url,
            file_size=file_size,
            generated_at=generated_at,
            expires_at=expires_at
        )

    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/download/{report_id}/{filename}")
async def download_report(report_id: str, filename: str):
    """
    Download generated report

    Returns the report file for download.
    """
    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )

    # Determine media type
    media_type = "text/html" if filename.endswith(".html") else "application/pdf"

    logger.info(f"Downloading report: {report_id} ({filename})")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@router.delete("/delete/{report_id}")
async def delete_report(report_id: str):
    """
    Delete report

    Removes report files from storage.
    """
    # Find files with this report_id
    deleted = []

    for file_path in REPORTS_DIR.glob(f"report_{report_id}.*"):
        file_path.unlink()
        deleted.append(file_path.name)
        logger.info(f"Deleted report file: {file_path.name}")

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )

    return {
        "message": f"Report deleted: {report_id}",
        "files_deleted": deleted
    }


@router.post("/cleanup-expired")
async def cleanup_expired():
    """
    Cleanup expired reports

    Removes report files older than expiration period.
    """
    expiration_seconds = settings.REPORT_EXPIRATION_DAYS * 24 * 60 * 60
    cutoff_time = datetime.utcnow().timestamp() - expiration_seconds

    deleted = []

    for file_path in REPORTS_DIR.glob("report_*"):
        # Check file modification time
        if file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()
            deleted.append(file_path.name)
            logger.info(f"Deleted expired report: {file_path.name}")

    return {
        "message": f"Cleanup completed",
        "files_deleted": len(deleted),
        "files": deleted
    }
