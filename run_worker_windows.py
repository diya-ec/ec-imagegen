from redis import Redis
from rq import Queue
from rq.timeouts import TimerDeathPenalty
from rq.worker import SimpleWorker

from app.core.config import get_settings

settings = get_settings()


class WindowsWorker(SimpleWorker):
    """
    RQ's default death-penalty (job timeout enforcement) uses SIGALRM, which
    doesn't exist on Windows. TimerDeathPenalty is a thread-based alternative
    that works cross-platform. Combined with SimpleWorker (no os.fork), this
    lets RQ run natively on Windows for local dev.
    """
    death_penalty_class = TimerDeathPenalty


if __name__ == "__main__":
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)
    worker = WindowsWorker([queue], connection=redis_conn)
    worker.work()