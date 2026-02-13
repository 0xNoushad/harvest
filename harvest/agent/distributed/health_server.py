"""
Simple health check server for Render free tier.

Render free tier sleeps after 15 min inactivity.
This server responds to health checks to keep worker alive.
"""

from aiohttp import web
import logging

logger = logging.getLogger(__name__)


async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "worker_id": request.app.get("worker_id", "unknown")
    })


async def status(request):
    """Status endpoint with more details."""
    worker = request.app.get("worker")
    
    if worker:
        status_data = worker.get_status()
    else:
        status_data = {"status": "initializing"}
    
    return web.json_response(status_data)


def create_health_server(worker_id: str, port: int = 8080):
    """
    Create health check server.
    
    Args:
        worker_id: Worker identifier
        port: Port to listen on
    
    Returns:
        aiohttp Application
    """
    app = web.Application()
    app["worker_id"] = worker_id
    
    # Add routes
    app.router.add_get("/health", health_check)
    app.router.add_get("/status", status)
    app.router.add_get("/", health_check)  # Root also returns health
    
    logger.info(f"Health server created for {worker_id} on port {port}")
    
    return app


async def run_health_server(worker_id: str, worker=None, port: int = 8080):
    """
    Run health check server.
    
    Args:
        worker_id: Worker identifier
        worker: Worker instance (optional)
        port: Port to listen on
    """
    app = create_health_server(worker_id, port)
    
    if worker:
        app["worker"] = worker
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logger.info(f"Health server running on port {port}")
    
    return runner


if __name__ == "__main__":
    import asyncio
    import os
    
    worker_id = os.getenv("WORKER_ID", "worker_test")
    port = int(os.getenv("PORT", "8080"))
    
    async def main():
        runner = await run_health_server(worker_id, port=port)
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            await runner.cleanup()
    
    asyncio.run(main())
