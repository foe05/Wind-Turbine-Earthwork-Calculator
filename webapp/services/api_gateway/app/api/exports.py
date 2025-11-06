"""
Export API - GeoPackage exports for projects and jobs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import psycopg2
import os
import tempfile
from typing import Optional
from uuid import UUID

from app.core.auth import get_current_user
from app.core.database import get_db_connection

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/projects/{project_id}/geopackage")
async def export_project_geopackage(
    project_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Export all sites and results from a project as GeoPackage.

    Creates a .gpkg file with:
    - Project metadata
    - All sites/locations with geometries
    - Calculation results
    - Job information
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Verify project ownership
        cur.execute("""
            SELECT id, name, use_case, crs, utm_zone, metadata
            FROM projects
            WHERE id = %s AND user_id = %s
        """, (str(project_id), current_user['id']))

        project = cur.fetchone()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projekt nicht gefunden"
            )

        project_name = project[1]
        use_case = project[2]
        crs_name = project[3]
        utm_zone = project[4]

        # Determine CRS EPSG code from project
        if 'UTM' in crs_name.upper():
            # Assuming Northern Hemisphere for now
            epsg_code = f"EPSG:326{utm_zone:02d}"
        else:
            epsg_code = "EPSG:4326"  # WGS84 fallback

        # Fetch all sites/jobs for this project
        cur.execute("""
            SELECT
                s.id,
                s.name,
                s.location_utm,
                s.foundation_type,
                s.foundation_diameter,
                s.foundation_depth,
                s.soil_type,
                s.bulk_density,
                j.id as job_id,
                j.status,
                j.results,
                j.created_at,
                j.completed_at
            FROM sites s
            LEFT JOIN jobs j ON s.id = j.site_id
            WHERE s.project_id = %s
            ORDER BY s.created_at
        """, (str(project_id),))

        sites_data = cur.fetchall()

        if not sites_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keine Sites im Projekt gefunden"
            )

        # Prepare data for GeoDataFrame
        features = []

        for site in sites_data:
            site_id, site_name, location_utm, foundation_type, foundation_diameter, \
            foundation_depth, soil_type, bulk_density, job_id, job_status, \
            results, created_at, completed_at = site

            # Parse location (assuming it's stored as "POINT(x y)")
            if location_utm:
                # Extract coordinates from WKT
                coords_str = location_utm.replace('POINT(', '').replace(')', '')
                x, y = map(float, coords_str.split())
                geometry = Point(x, y)
            else:
                continue  # Skip sites without location

            # Build feature attributes
            feature = {
                'site_id': str(site_id),
                'site_name': site_name or '',
                'foundation_type': foundation_type or '',
                'foundation_diameter': foundation_diameter,
                'foundation_depth': foundation_depth,
                'soil_type': soil_type or '',
                'bulk_density': bulk_density,
                'job_id': str(job_id) if job_id else None,
                'job_status': job_status or '',
                'created_at': str(created_at) if created_at else '',
                'completed_at': str(completed_at) if completed_at else '',
                'geometry': geometry
            }

            # Add results if available
            if results and job_status == 'completed':
                feature['cut_volume'] = results.get('cut_volume')
                feature['fill_volume'] = results.get('fill_volume')
                feature['total_volume'] = results.get('total_volume')
                feature['foundation_volume'] = results.get('foundation_volume')
                feature['surface_area'] = results.get('surface_area')
            else:
                feature['cut_volume'] = None
                feature['fill_volume'] = None
                feature['total_volume'] = None
                feature['foundation_volume'] = None
                feature['surface_area'] = None

            features.append(feature)

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(features, crs=epsg_code)

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        filename = f"{project_name.replace(' ', '_')}_{project_id}.gpkg"
        filepath = os.path.join(temp_dir, filename)

        # Export to GeoPackage
        gdf.to_file(filepath, driver='GPKG', layer='sites')

        # Return file
        return FileResponse(
            filepath,
            media_type='application/geopackage+sqlite3',
            filename=filename,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Export: {str(e)}"
        )
    finally:
        cur.close()
        conn.close()


@router.get("/jobs/{job_id}/geopackage")
async def export_job_geopackage(
    job_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Export a single job result as GeoPackage.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch job with ownership verification
        cur.execute("""
            SELECT
                j.id,
                j.status,
                j.results,
                s.id as site_id,
                s.name as site_name,
                s.location_utm,
                s.foundation_type,
                s.foundation_diameter,
                s.foundation_depth,
                s.soil_type,
                s.bulk_density,
                p.name as project_name,
                p.use_case,
                p.crs,
                p.utm_zone,
                j.created_at,
                j.completed_at
            FROM jobs j
            JOIN sites s ON j.site_id = s.id
            JOIN projects p ON s.project_id = p.id
            WHERE j.id = %s AND p.user_id = %s
        """, (str(job_id), current_user['id']))

        job_data = cur.fetchone()
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job nicht gefunden"
            )

        if job_data[1] != 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job ist noch nicht abgeschlossen"
            )

        # Extract data
        job_id, job_status, results, site_id, site_name, location_utm, \
        foundation_type, foundation_diameter, foundation_depth, soil_type, \
        bulk_density, project_name, use_case, crs_name, utm_zone, \
        created_at, completed_at = job_data

        # Determine CRS
        if 'UTM' in crs_name.upper():
            epsg_code = f"EPSG:326{utm_zone:02d}"
        else:
            epsg_code = "EPSG:4326"

        # Parse location
        if location_utm:
            coords_str = location_utm.replace('POINT(', '').replace(')', '')
            x, y = map(float, coords_str.split())
            geometry = Point(x, y)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site hat keine Geometrie"
            )

        # Build feature
        feature = {
            'job_id': str(job_id),
            'site_id': str(site_id),
            'site_name': site_name or '',
            'project_name': project_name or '',
            'use_case': use_case or '',
            'foundation_type': foundation_type or '',
            'foundation_diameter': foundation_diameter,
            'foundation_depth': foundation_depth,
            'soil_type': soil_type or '',
            'bulk_density': bulk_density,
            'status': job_status,
            'cut_volume': results.get('cut_volume') if results else None,
            'fill_volume': results.get('fill_volume') if results else None,
            'total_volume': results.get('total_volume') if results else None,
            'foundation_volume': results.get('foundation_volume') if results else None,
            'surface_area': results.get('surface_area') if results else None,
            'created_at': str(created_at) if created_at else '',
            'completed_at': str(completed_at) if completed_at else '',
            'geometry': geometry
        }

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame([feature], crs=epsg_code)

        # Create temporary file
        temp_dir = tempfile.gettempdir()
        filename = f"{site_name.replace(' ', '_')}_{job_id}.gpkg"
        filepath = os.path.join(temp_dir, filename)

        # Export to GeoPackage
        gdf.to_file(filepath, driver='GPKG', layer='job_result')

        # Return file
        return FileResponse(
            filepath,
            media_type='application/geopackage+sqlite3',
            filename=filename,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Export: {str(e)}"
        )
    finally:
        cur.close()
        conn.close()
