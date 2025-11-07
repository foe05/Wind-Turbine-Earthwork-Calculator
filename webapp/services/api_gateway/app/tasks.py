"""
Background tasks for Geo-Engineering Platform
"""
from celery import Task
import httpx
import logging
import os
from typing import Dict, Any, List
import json

from app.worker import celery_app

logger = logging.getLogger(__name__)

# Service URLs
DEM_SERVICE_URL = os.getenv("DEM_SERVICE_URL", "http://dem_service:8002")
CALCULATION_SERVICE_URL = os.getenv("CALCULATION_SERVICE_URL", "http://calculation_service:8003")
COST_SERVICE_URL = os.getenv("COST_SERVICE_URL", "http://cost_service:8004")
REPORT_SERVICE_URL = os.getenv("REPORT_SERVICE_URL", "http://report_service:8005")


class ProgressTrackingTask(Task):
    """Base task with progress tracking via state updates"""

    def update_progress(self, progress: int, message: str = "", data: Dict = None):
        """
        Update task progress

        Args:
            progress: Progress percentage (0-100)
            message: Status message
            data: Additional data to include in state
        """
        state_data = {
            'progress': progress,
            'message': message,
            'data': data or {}
        }
        self.update_state(
            state='PROGRESS',
            meta=state_data
        )
        logger.info(f"Task {self.request.id}: {progress}% - {message}")


@celery_app.task(
    name='app.tasks.calculate_wka_site',
    base=ProgressTrackingTask,
    bind=True,
    max_retries=3
)
def calculate_wka_site(
    self,
    job_id: str,
    project_id: str,
    site_data: Dict[str, Any],
    cost_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Background task: Calculate WKA site earthwork and costs

    Args:
        job_id: Job UUID
        project_id: Project UUID
        site_data: Site calculation parameters
        cost_params: Cost calculation parameters

    Returns:
        Complete calculation results
    """
    try:
        logger.info(f"Starting WKA calculation for job {job_id}")

        # Step 1: Fetch DEM (20%)
        self.update_progress(20, "Fetching DEM data...")
        with httpx.Client(timeout=120.0) as client:
            dem_response = client.post(
                f"{DEM_SERVICE_URL}/dem/fetch",
                json={
                    "crs": site_data["crs"],
                    "center_x": site_data["center_x"],
                    "center_y": site_data["center_y"],
                    "buffer_meters": site_data.get("buffer_meters", 250)
                }
            )
            dem_response.raise_for_status()
            dem_data = dem_response.json()
            dem_id = dem_data["dem_id"]

        # Step 2: Calculate earthwork (50%)
        self.update_progress(50, "Calculating earthwork volumes...")
        with httpx.Client(timeout=120.0) as client:
            calc_response = client.post(
                f"{CALCULATION_SERVICE_URL}/calc/wka/site",
                json={
                    "dem_id": dem_id,
                    **site_data
                }
            )
            calc_response.raise_for_status()
            calc_data = calc_response.json()

        # Step 3: Calculate costs (70%)
        self.update_progress(70, "Calculating costs...")
        with httpx.Client(timeout=60.0) as client:
            cost_response = client.post(
                f"{COST_SERVICE_URL}/costs/calculate",
                json={
                    "foundation_volume": calc_data["foundation_volume"],
                    "crane_cut": calc_data["total_cut"],
                    "crane_fill": calc_data["total_fill"],
                    "platform_area": calc_data["platform_area"],
                    **cost_params
                }
            )
            cost_response.raise_for_status()
            cost_data = cost_response.json()

        # Step 4: Combine results (90%)
        self.update_progress(90, "Finalizing results...")

        result = {
            "job_id": job_id,
            "project_id": project_id,
            "site_data": calc_data,
            "cost_data": cost_data,
            "dem_id": dem_id,
            "status": "completed"
        }

        self.update_progress(100, "Calculation completed!")
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error in WKA calculation: {e}")
        self.update_progress(0, f"Error: {str(e)}")
        raise self.retry(exc=e, countdown=60)

    except Exception as e:
        logger.error(f"Error in WKA calculation: {e}", exc_info=True)
        self.update_progress(0, f"Error: {str(e)}")
        raise


@celery_app.task(
    name='app.tasks.calculate_road_project',
    base=ProgressTrackingTask,
    bind=True,
    max_retries=3
)
def calculate_road_project(
    self,
    job_id: str,
    project_id: str,
    road_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Background task: Calculate road earthwork

    Args:
        job_id: Job UUID
        project_id: Project UUID
        road_data: Road calculation parameters

    Returns:
        Road calculation results
    """
    try:
        logger.info(f"Starting road calculation for job {job_id}")

        # Step 1: Fetch DEM (30%)
        self.update_progress(30, "Fetching DEM data for road centerline...")
        with httpx.Client(timeout=120.0) as client:
            # Calculate bounds from centerline
            centerline = road_data["centerline"]
            xs = [p[0] for p in centerline]
            ys = [p[1] for p in centerline]
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2

            dem_response = client.post(
                f"{DEM_SERVICE_URL}/dem/fetch",
                json={
                    "crs": road_data["crs"],
                    "center_x": center_x,
                    "center_y": center_y,
                    "buffer_meters": road_data.get("buffer_meters", 500)
                }
            )
            dem_response.raise_for_status()
            dem_data = dem_response.json()
            dem_id = dem_data["dem_id"]

        # Step 2: Calculate road earthwork (80%)
        self.update_progress(80, "Calculating road earthwork...")
        with httpx.Client(timeout=180.0) as client:
            calc_response = client.post(
                f"{CALCULATION_SERVICE_URL}/road/calculate",
                json={
                    "dem_id": dem_id,
                    **road_data
                }
            )
            calc_response.raise_for_status()
            calc_data = calc_response.json()

        self.update_progress(100, "Road calculation completed!")

        return {
            "job_id": job_id,
            "project_id": project_id,
            "road_data": calc_data,
            "dem_id": dem_id,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error in road calculation: {e}", exc_info=True)
        self.update_progress(0, f"Error: {str(e)}")
        raise


@celery_app.task(
    name='app.tasks.calculate_solar_project',
    base=ProgressTrackingTask,
    bind=True,
    max_retries=3
)
def calculate_solar_project(
    self,
    job_id: str,
    project_id: str,
    solar_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Background task: Calculate solar park earthwork

    Args:
        job_id: Job UUID
        project_id: Project UUID
        solar_data: Solar park calculation parameters

    Returns:
        Solar park calculation results
    """
    try:
        logger.info(f"Starting solar park calculation for job {job_id}")

        # Step 1: Fetch DEM (30%)
        self.update_progress(30, "Fetching DEM data for solar site...")
        with httpx.Client(timeout=120.0) as client:
            # Calculate bounds from boundary
            boundary = solar_data["boundary"]
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2

            dem_response = client.post(
                f"{DEM_SERVICE_URL}/dem/fetch",
                json={
                    "crs": solar_data["crs"],
                    "center_x": center_x,
                    "center_y": center_y,
                    "buffer_meters": solar_data.get("buffer_meters", 500)
                }
            )
            dem_response.raise_for_status()
            dem_data = dem_response.json()
            dem_id = dem_data["dem_id"]

        # Step 2: Calculate solar park (80%)
        self.update_progress(80, "Calculating solar park layout and earthwork...")
        with httpx.Client(timeout=180.0) as client:
            calc_response = client.post(
                f"{CALCULATION_SERVICE_URL}/solar/calculate",
                json={
                    "dem_id": dem_id,
                    **solar_data
                }
            )
            calc_response.raise_for_status()
            calc_data = calc_response.json()

        self.update_progress(100, "Solar park calculation completed!")

        return {
            "job_id": job_id,
            "project_id": project_id,
            "solar_data": calc_data,
            "dem_id": dem_id,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error in solar park calculation: {e}", exc_info=True)
        self.update_progress(0, f"Error: {str(e)}")
        raise


@celery_app.task(
    name='app.tasks.analyze_terrain',
    base=ProgressTrackingTask,
    bind=True,
    max_retries=3
)
def analyze_terrain(
    self,
    job_id: str,
    project_id: str,
    terrain_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Background task: Terrain analysis

    Args:
        job_id: Job UUID
        project_id: Project UUID
        terrain_data: Terrain analysis parameters

    Returns:
        Terrain analysis results
    """
    try:
        logger.info(f"Starting terrain analysis for job {job_id}")

        # Step 1: Fetch DEM (30%)
        self.update_progress(30, "Fetching DEM data for analysis area...")
        with httpx.Client(timeout=120.0) as client:
            # Calculate bounds from polygon
            polygon = terrain_data["polygon"]
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2

            dem_response = client.post(
                f"{DEM_SERVICE_URL}/dem/fetch",
                json={
                    "crs": terrain_data["crs"],
                    "center_x": center_x,
                    "center_y": center_y,
                    "buffer_meters": terrain_data.get("buffer_meters", 500)
                }
            )
            dem_response.raise_for_status()
            dem_data = dem_response.json()
            dem_id = dem_data["dem_id"]

        # Step 2: Perform terrain analysis (80%)
        self.update_progress(80, f"Performing {terrain_data['analysis_type']} analysis...")
        with httpx.Client(timeout=180.0) as client:
            calc_response = client.post(
                f"{CALCULATION_SERVICE_URL}/terrain/analyze",
                json={
                    "dem_id": dem_id,
                    **terrain_data
                }
            )
            calc_response.raise_for_status()
            calc_data = calc_response.json()

        self.update_progress(100, "Terrain analysis completed!")

        return {
            "job_id": job_id,
            "project_id": project_id,
            "terrain_data": calc_data,
            "dem_id": dem_id,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error in terrain analysis: {e}", exc_info=True)
        self.update_progress(0, f"Error: {str(e)}")
        raise


@celery_app.task(
    name='app.tasks.generate_report',
    base=ProgressTrackingTask,
    bind=True,
    max_retries=3
)
def generate_report(
    self,
    job_id: str,
    report_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Background task: Generate report

    Args:
        job_id: Job UUID
        report_data: Report generation parameters

    Returns:
        Report generation results with download URL
    """
    try:
        logger.info(f"Starting report generation for job {job_id}")

        self.update_progress(50, "Generating report...")

        with httpx.Client(timeout=180.0) as client:
            report_response = client.post(
                f"{REPORT_SERVICE_URL}/report/generate",
                json=report_data
            )
            report_response.raise_for_status()
            report_result = report_response.json()

        self.update_progress(100, "Report generated!")

        return {
            "job_id": job_id,
            "report_result": report_result,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Error in report generation: {e}", exc_info=True)
        self.update_progress(0, f"Error: {str(e)}")
        raise
