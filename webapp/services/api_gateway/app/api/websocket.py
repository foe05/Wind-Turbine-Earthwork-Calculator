"""
WebSocket endpoints for real-time progress updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from celery.result import AsyncResult
import asyncio
import logging
import json
from typing import Dict, Set

from app.worker import celery_app

logger = logging.getLogger(__name__)
router = APIRouter()

# Connection manager
class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept and register a WebSocket connection"""
        await websocket.accept()

        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()

        self.active_connections[job_id].add(websocket)
        logger.info(f"WebSocket connected for job {job_id}. Total connections: {len(self.active_connections[job_id])}")

    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a WebSocket connection"""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)

            if len(self.active_connections[job_id]) == 0:
                del self.active_connections[job_id]

        logger.info(f"WebSocket disconnected for job {job_id}")

    async def send_to_job(self, job_id: str, message: dict):
        """Send message to all connections listening to a job"""
        if job_id not in self.active_connections:
            return

        disconnected = set()

        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, job_id)


manager = ConnectionManager()


@router.websocket("/ws/job/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for job progress updates

    Clients connect to this endpoint to receive real-time progress
    updates for a specific job.

    URL: ws://localhost:8000/ws/job/{job_id}
    """
    await manager.connect(websocket, job_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "message": "Connected to job progress stream"
        })

        # Check if job exists
        result = AsyncResult(job_id, app=celery_app)

        # Poll for updates
        while True:
            # Get task state
            state = result.state
            info = result.info if result.info else {}

            # Prepare message
            message = {
                "type": "progress",
                "job_id": job_id,
                "state": state,
            }

            if state == 'PENDING':
                message.update({
                    "progress": 0,
                    "message": "Task pending..."
                })

            elif state == 'PROGRESS':
                # Custom progress state with metadata
                message.update({
                    "progress": info.get('progress', 0),
                    "message": info.get('message', ''),
                    "data": info.get('data', {})
                })

            elif state == 'SUCCESS':
                message.update({
                    "progress": 100,
                    "message": "Task completed successfully!",
                    "result": result.result
                })

                await websocket.send_json(message)

                # Send completion message and close
                await websocket.send_json({
                    "type": "completed",
                    "job_id": job_id,
                    "result": result.result
                })
                break

            elif state == 'FAILURE':
                message.update({
                    "progress": 0,
                    "message": f"Task failed: {str(info)}",
                    "error": str(info)
                })

                await websocket.send_json(message)

                # Send failure message and close
                await websocket.send_json({
                    "type": "failed",
                    "job_id": job_id,
                    "error": str(info)
                })
                break

            elif state == 'RETRY':
                message.update({
                    "progress": 0,
                    "message": "Task is retrying...",
                })

            # Send progress update
            await websocket.send_json(message)

            # Wait before next poll
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from job {job_id}")
        manager.disconnect(websocket, job_id)

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "job_id": job_id,
                "message": str(e)
            })
        except:
            pass
        manager.disconnect(websocket, job_id)


@router.get("/job/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get current status of a background job

    Alternative to WebSocket for simple status checks.
    """
    result = AsyncResult(job_id, app=celery_app)

    response = {
        "job_id": job_id,
        "state": result.state,
    }

    if result.state == 'PENDING':
        response.update({
            "progress": 0,
            "message": "Task pending..."
        })

    elif result.state == 'PROGRESS':
        info = result.info if result.info else {}
        response.update({
            "progress": info.get('progress', 0),
            "message": info.get('message', ''),
            "data": info.get('data', {})
        })

    elif result.state == 'SUCCESS':
        response.update({
            "progress": 100,
            "message": "Task completed successfully!",
            "result": result.result
        })

    elif result.state == 'FAILURE':
        response.update({
            "progress": 0,
            "message": f"Task failed",
            "error": str(result.info)
        })

    elif result.state == 'RETRY':
        response.update({
            "progress": 0,
            "message": "Task is retrying..."
        })

    return response


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a background job

    Sends termination signal to the Celery task.
    """
    result = AsyncResult(job_id, app=celery_app)

    if result.state in ['PENDING', 'PROGRESS', 'RETRY']:
        result.revoke(terminate=True)

        return {
            "job_id": job_id,
            "message": "Job cancellation requested",
            "previous_state": result.state
        }
    else:
        return {
            "job_id": job_id,
            "message": f"Job cannot be cancelled (state: {result.state})",
            "state": result.state
        }
