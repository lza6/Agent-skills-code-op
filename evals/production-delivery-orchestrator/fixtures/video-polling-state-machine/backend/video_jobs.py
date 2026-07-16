TERMINAL_VIDEO_JOB_STATES = {"completed", "failed"}


def submit_video_job(payload: dict) -> str:
    return enqueue_video_job(payload)


def enqueue_video_job(payload: dict) -> str:
    return "job-123"


def process_video_job(job_id: str, succeeds: bool) -> dict:
    return {
        "id": job_id,
        "status": "completed" if succeeds else "failed",
    }
