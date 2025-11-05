"""
Background Jobs API
Endpoints for submitting and managing background calculation jobs
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
import uuid
import logging

from app.tasks import (
    calculate_wka_site,
    calculate_road_project,
    calculate_solar_project,
    analyze_terrain,
    generate_report
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


# Request models
class WKAJobRequest(BaseModel):
    """Request to submit WKA calculation job"""
    project_id: str = Field(..., description="Project UUID")
    site_data: Dict[str, Any] = Field(..., description="Site calculation parameters")
    cost_params: Dict[str, Any] = Field(..., description="Cost calculation parameters")


class RoadJobRequest(BaseModel):
    """Request to submit Road calculation job"""
    project_id: str = Field(..., description="Project UUID")
    road_data: Dict[str, Any] = Field(..., description="Road calculation parameters")


class SolarJobRequest(BaseModel):
    """Request to submit Solar park calculation job"""
    project_id: str = Field(..., description="Project UUID")
    solar_data: Dict[str, Any] = Field(..., description="Solar park calculation parameters")


class TerrainJobRequest(BaseModel):
    """Request to submit Terrain analysis job"""
    project_id: str = Field(..., description="Project UUID")
    terrain_data: Dict[str, Any] = Field(..., description="Terrain analysis parameters")


class ReportJobRequest(BaseModel):
    """Request to submit Report generation job"""
    report_data: Dict[str, Any] = Field(..., description="Report generation parameters")


# Response model
class JobResponse(BaseModel):
    """Response with job ID for tracking"""
    job_id: str = Field(..., description="Job UUID for tracking progress")
    message: str = Field(..., description="Status message")
    websocket_url: str = Field(..., description="WebSocket URL for real-time updates")
    status_url: str = Field(..., description="HTTP endpoint for status polling")


@router.post("/wka/submit", response_model=JobResponse)
async def submit_wka_job(request: WKAJobRequest):
    """
    Submit WKA calculation as background job

    The job will:
    1. Fetch DEM data
    2. Calculate earthwork volumes
    3. Calculate costs

    Use WebSocket or status endpoint to track progress.
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Submit task
        result = calculate_wka_site.apply_async(
            kwargs={
                "job_id": job_id,
                "project_id": request.project_id,
                "site_data": request.site_data,
                "cost_params": request.cost_params
            },
            task_id=job_id
        )

        logger.info(f"Submitted WKA job: {job_id}")

        return JobResponse(
            job_id=job_id,
            message="WKA calculation job submitted successfully",
            websocket_url=f"ws://localhost:8000/ws/job/{job_id}",
            status_url=f"/job/{job_id}/status"
        )

    except Exception as e:
        logger.error(f"Error submitting WKA job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.post("/road/submit", response_model=JobResponse)
async def submit_road_job(request: RoadJobRequest):
    """
    Submit Road calculation as background job

    The job will:
    1. Fetch DEM data
    2. Calculate road earthwork

    Use WebSocket or status endpoint to track progress.
    """
    try:
        job_id = str(uuid.uuid4())

        result = calculate_road_project.apply_async(
            kwargs={
                "job_id": job_id,
                "project_id": request.project_id,
                "road_data": request.road_data
            },
            task_id=job_id
        )

        logger.info(f"Submitted Road job: {job_id}")

        return JobResponse(
            job_id=job_id,
            message="Road calculation job submitted successfully",
            websocket_url=f"ws://localhost:8000/ws/job/{job_id}",
            status_url=f"/job/{job_id}/status"
        )

    except Exception as e:
        logger.error(f"Error submitting Road job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.post("/solar/submit", response_model=JobResponse)
async def submit_solar_job(request: SolarJobRequest):
    """
    Submit Solar park calculation as background job

    The job will:
    1. Fetch DEM data
    2. Calculate solar park layout and earthwork

    Use WebSocket or status endpoint to track progress.
    """
    try:
        job_id = str(uuid.uuid4())

        result = calculate_solar_project.apply_async(
            kwargs={
                "job_id": job_id,
                "project_id": request.project_id,
                "solar_data": request.solar_data
            },
            task_id=job_id
        )

        logger.info(f"Submitted Solar job: {job_id}")

        return JobResponse(
            job_id=job_id,
            message="Solar park calculation job submitted successfully",
            websocket_url=f"ws://localhost:8000/ws/job/{job_id}",
            status_url=f"/job/{job_id}/status"
        )

    except Exception as e:
        logger.error(f"Error submitting Solar job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.post("/terrain/submit", response_model=JobResponse)
async def submit_terrain_job(request: TerrainJobRequest):
    """
    Submit Terrain analysis as background job

    The job will:
    1. Fetch DEM data
    2. Perform terrain analysis

    Use WebSocket or status endpoint to track progress.
    """
    try:
        job_id = str(uuid.uuid4())

        result = analyze_terrain.apply_async(
            kwargs={
                "job_id": job_id,
                "project_id": request.project_id,
                "terrain_data": request.terrain_data
            },
            task_id=job_id
        )

        logger.info(f"Submitted Terrain job: {job_id}")

        return JobResponse(
            job_id=job_id,
            message="Terrain analysis job submitted successfully",
            websocket_url=f"ws://localhost:8000/ws/job/{job_id}",
            status_url=f"/job/{job_id}/status"
        )

    except Exception as e:
        logger.error(f"Error submitting Terrain job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )


@router.post("/report/submit", response_model=JobResponse)
async def submit_report_job(request: ReportJobRequest):
    """
    Submit Report generation as background job

    Generates HTML or PDF report based on provided data.

    Use WebSocket or status endpoint to track progress.
    """
    try:
        job_id = str(uuid.uuid4())

        result = generate_report.apply_async(
            kwargs={
                "job_id": job_id,
                "report_data": request.report_data
            },
            task_id=job_id
        )

        logger.info(f"Submitted Report job: {job_id}")

        return JobResponse(
            job_id=job_id,
            message="Report generation job submitted successfully",
            websocket_url=f"ws://localhost:8000/ws/job/{job_id}",
            status_url=f"/job/{job_id}/status"
        )

    except Exception as e:
        logger.error(f"Error submitting Report job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit job: {str(e)}"
        )
