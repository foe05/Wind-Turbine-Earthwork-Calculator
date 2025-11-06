"""
Project Management API
CRUD operations for projects
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import logging
from uuid import UUID

from app.core.database import get_db_connection
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


# Pydantic Models
class ProjectBase(BaseModel):
    """Base project model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    use_case: Literal["wka", "road", "solar", "terrain"]
    crs: str = Field(..., pattern=r"^EPSG:\d+$")
    utm_zone: int = Field(..., ge=1, le=60)


class ProjectCreate(ProjectBase):
    """Create project request"""
    bounds: Optional[dict] = Field(None, description="GeoJSON Polygon (WGS84)")
    metadata: Optional[dict] = {}


class ProjectUpdate(BaseModel):
    """Update project request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    bounds: Optional[dict] = None
    metadata: Optional[dict] = None


class ProjectResponse(ProjectBase):
    """Project response"""
    id: UUID
    user_id: UUID
    bounds: Optional[dict] = None
    metadata: dict
    created_at: datetime
    updated_at: datetime

    # Statistics
    job_count: Optional[int] = 0
    completed_jobs: Optional[int] = 0
    last_calculation: Optional[datetime] = None


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create new project

    Creates a new project for the authenticated user.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Convert bounds to PostGIS geometry if provided
        bounds_wkt = None
        if project.bounds:
            # Assuming bounds is GeoJSON Polygon
            coordinates = project.bounds.get("coordinates", [[]])[0]
            points = ", ".join([f"{lon} {lat}" for lon, lat in coordinates])
            bounds_wkt = f"POLYGON(({points}))"

        # Insert project
        cur.execute("""
            INSERT INTO projects (user_id, use_case, name, description, crs, utm_zone, bounds, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
            RETURNING id, created_at, updated_at
        """, (
            current_user["id"],
            project.use_case,
            project.name,
            project.description,
            project.crs,
            project.utm_zone,
            bounds_wkt,
            project.metadata or {}
        ))

        result = cur.fetchone()
        project_id, created_at, updated_at = result

        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Created project {project_id} for user {current_user['id']}")

        return ProjectResponse(
            id=project_id,
            user_id=current_user["id"],
            use_case=project.use_case,
            name=project.name,
            description=project.description,
            crs=project.crs,
            utm_zone=project.utm_zone,
            bounds=project.bounds,
            metadata=project.metadata or {},
            created_at=created_at,
            updated_at=updated_at,
            job_count=0,
            completed_jobs=0
        )

    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    use_case: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    List all projects for current user

    Returns paginated list of user's projects with job statistics.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build query
        where_clause = "WHERE p.user_id = %s"
        params = [current_user["id"]]

        if use_case:
            where_clause += " AND p.use_case = %s"
            params.append(use_case)

        query = f"""
            SELECT
                p.id, p.user_id, p.use_case, p.name, p.description,
                p.crs, p.utm_zone,
                ST_AsGeoJSON(p.bounds)::json as bounds,
                p.metadata, p.created_at, p.updated_at,
                COUNT(j.id) as job_count,
                COUNT(j.id) FILTER (WHERE j.status = 'completed') as completed_jobs,
                MAX(j.completed_at) as last_calculation
            FROM projects p
            LEFT JOIN jobs j ON p.id = j.project_id
            {where_clause}
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        projects = []
        for row in rows:
            projects.append(ProjectResponse(
                id=row[0],
                user_id=row[1],
                use_case=row[2],
                name=row[3],
                description=row[4],
                crs=row[5],
                utm_zone=row[6],
                bounds=row[7],
                metadata=row[8] or {},
                created_at=row[9],
                updated_at=row[10],
                job_count=row[11] or 0,
                completed_jobs=row[12] or 0,
                last_calculation=row[13]
            ))

        cur.close()
        conn.close()

        logger.info(f"Listed {len(projects)} projects for user {current_user['id']}")
        return projects

    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get project by ID

    Returns detailed project information with statistics.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                p.id, p.user_id, p.use_case, p.name, p.description,
                p.crs, p.utm_zone,
                ST_AsGeoJSON(p.bounds)::json as bounds,
                p.metadata, p.created_at, p.updated_at,
                COUNT(j.id) as job_count,
                COUNT(j.id) FILTER (WHERE j.status = 'completed') as completed_jobs,
                MAX(j.completed_at) as last_calculation
            FROM projects p
            LEFT JOIN jobs j ON p.id = j.project_id
            WHERE p.id = %s AND p.user_id = %s
            GROUP BY p.id
        """, (str(project_id), current_user["id"]))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        return ProjectResponse(
            id=row[0],
            user_id=row[1],
            use_case=row[2],
            name=row[3],
            description=row[4],
            crs=row[5],
            utm_zone=row[6],
            bounds=row[7],
            metadata=row[8] or {},
            created_at=row[9],
            updated_at=row[10],
            job_count=row[11] or 0,
            completed_jobs=row[12] or 0,
            last_calculation=row[13]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project: {str(e)}"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    updates: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update project

    Updates project fields. Only provided fields will be updated.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check ownership
        cur.execute("SELECT user_id FROM projects WHERE id = %s", (str(project_id),))
        result = cur.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if result[0] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this project"
            )

        # Build update query
        update_fields = []
        params = []

        if updates.name is not None:
            update_fields.append("name = %s")
            params.append(updates.name)

        if updates.description is not None:
            update_fields.append("description = %s")
            params.append(updates.description)

        if updates.bounds is not None:
            coordinates = updates.bounds.get("coordinates", [[]])[0]
            points = ", ".join([f"{lon} {lat}" for lon, lat in coordinates])
            bounds_wkt = f"POLYGON(({points}))"
            update_fields.append("bounds = ST_GeomFromText(%s, 4326)")
            params.append(bounds_wkt)

        if updates.metadata is not None:
            update_fields.append("metadata = %s")
            params.append(updates.metadata)

        if not update_fields:
            # No updates, return current project
            return await get_project(project_id, current_user)

        update_fields.append("updated_at = NOW()")
        params.append(str(project_id))

        query = f"""
            UPDATE projects
            SET {", ".join(update_fields)}
            WHERE id = %s
            RETURNING updated_at
        """

        cur.execute(query, params)
        conn.commit()

        cur.close()
        conn.close()

        logger.info(f"Updated project {project_id}")

        # Return updated project
        return await get_project(project_id, current_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete project

    Deletes project and all associated jobs (CASCADE).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check ownership
        cur.execute("SELECT user_id FROM projects WHERE id = %s", (str(project_id),))
        result = cur.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )

        if result[0] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this project"
            )

        # Delete project (CASCADE deletes jobs)
        cur.execute("DELETE FROM projects WHERE id = %s", (str(project_id),))
        conn.commit()

        cur.close()
        conn.close()

        logger.info(f"Deleted project {project_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )
