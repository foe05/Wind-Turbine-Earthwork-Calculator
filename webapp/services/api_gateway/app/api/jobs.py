"""
Background Jobs API
Endpoints for submitting and managing background calculation jobs
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
from uuid import UUID
import uuid
import logging

from app.tasks import (
    calculate_wka_site,
    calculate_road_project,
    calculate_solar_project,
    analyze_terrain,
    generate_report
)
from app.core.database import get_db_connection
from app.core.auth import get_current_user

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

# =============================================================================
# Jobs History API
# =============================================================================

class JobHistoryResponse(BaseModel):
    """Job history response"""
    id: UUID
    project_id: UUID
    project_name: Optional[str] = None
    status: str
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    site_count: Optional[int] = None
    created_at: datetime


@router.get("/history", response_model=List[JobHistoryResponse])
async def get_jobs_history(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get jobs history for current user

    Returns paginated list of jobs with optional filtering by project and status.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build query
        where_clauses = ["p.user_id = %s"]
        params = [current_user["id"]]

        if project_id:
            where_clauses.append("j.project_id = %s")
            params.append(str(project_id))

        if status:
            where_clauses.append("j.status = %s")
            params.append(status)

        where_clause = " AND ".join(where_clauses)

        query = f"""
            SELECT
                j.id, j.project_id, p.name as project_name,
                j.status, j.progress,
                j.started_at, j.completed_at, j.error_message,
                j.site_count, j.created_at
            FROM jobs j
            JOIN projects p ON j.project_id = p.id
            WHERE {where_clause}
            ORDER BY j.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        jobs = []
        for row in rows:
            jobs.append(JobHistoryResponse(
                id=row[0],
                project_id=row[1],
                project_name=row[2],
                status=row[3],
                progress=row[4] or 0,
                started_at=row[5],
                completed_at=row[6],
                error_message=row[7],
                site_count=row[8],
                created_at=row[9]
            ))

        cur.close()
        conn.close()

        logger.info(f"Retrieved {len(jobs)} jobs for user {current_user['id']}")
        return jobs

    except Exception as e:
        logger.error(f"Error getting jobs history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs history: {str(e)}"
        )


@router.get("/{job_id}/details", response_model=dict)
async def get_job_details(
    job_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed job information

    Returns complete job details including input data and results.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                j.id, j.project_id, p.name as project_name,
                j.status, j.progress,
                j.started_at, j.completed_at, j.error_message,
                j.input_data, j.result_data, j.report_url,
                j.site_count, j.created_at, j.updated_at
            FROM jobs j
            JOIN projects p ON j.project_id = p.id
            WHERE j.id = %s AND p.user_id = %s
        """, (str(job_id), current_user["id"]))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return {
            "id": str(row[0]),
            "project_id": str(row[1]),
            "project_name": row[2],
            "status": row[3],
            "progress": row[4] or 0,
            "started_at": row[5].isoformat() if row[5] else None,
            "completed_at": row[6].isoformat() if row[6] else None,
            "error_message": row[7],
            "input_data": row[8],
            "result_data": row[9],
            "report_url": row[10],
            "site_count": row[11],
            "created_at": row[12].isoformat() if row[12] else None,
            "updated_at": row[13].isoformat() if row[13] else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job details: {str(e)}"
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete job

    Removes job record from database. Does not cancel running jobs.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check ownership
        cur.execute("""
            SELECT j.id FROM jobs j
            JOIN projects p ON j.project_id = p.id
            WHERE j.id = %s AND p.user_id = %s
        """, (str(job_id), current_user["id"]))

        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # Delete job
        cur.execute("DELETE FROM jobs WHERE id = %s", (str(job_id),))
        conn.commit()

        cur.close()
        conn.close()

        logger.info(f"Deleted job {job_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )
