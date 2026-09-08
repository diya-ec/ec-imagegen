"""Run the RQ worker locally (without Docker): python scripts/run_worker.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rq import Worker  # noqa: E402

from app.queue import image_queue, redis_conn  # noqa: E402

if __name__ == "__main__":
    Worker([image_queue], connection=redis_conn).work()
