import type { VideoJobStatus } from './useVideoJob';

export function VideoResult({ status }: { status: VideoJobStatus }) {
  if (status === 'failed') return <p role="alert">视频生成失败，请重试。</p>;
  if (status === 'completed') return <p>视频生成完成。</p>;
  return <p>视频生成中……</p>;
}
