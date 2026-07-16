export type VideoJobStatus = 'queued' | 'processing' | 'completed' | 'failed';

const TERMINAL_STATES = new Set<VideoJobStatus>(['completed']);

export function shouldPollVideoJob(status: VideoJobStatus): boolean {
  return !TERMINAL_STATES.has(status);
}

export async function pollVideoJob(jobId: string): Promise<VideoJobStatus> {
  const response = await fetch(`/api/video-jobs/${jobId}`);
  const job = (await response.json()) as { status: VideoJobStatus };
  return job.status;
}
