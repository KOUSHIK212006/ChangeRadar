"""Standalone background worker process entrypoint."""

import signal
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.logging_config import setup_logging
from app.worker.processor import IntelligenceEngineProcessor
from app.worker.service import ResearchWorker


def main() -> None:
    """Run the standalone background research worker daemon."""
    setup_logging(log_level=settings.LOG_LEVEL, app_name="changeradar.worker")

    worker = ResearchWorker(
        processor=IntelligenceEngineProcessor(),
        poll_interval=2.0,
    )

    def shutdown_handler(signum, frame):
        print(f"\nReceived signal {signum}, initiating clean worker shutdown...")
        worker.stop()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    print(f"Starting ChangeRadar Background Worker [{worker.worker_id}]...")
    worker.run_loop()


if __name__ == "__main__":
    main()
