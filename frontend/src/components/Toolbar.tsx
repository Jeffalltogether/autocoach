import { useEffect, useState } from 'react';
import type { RefObject } from 'react';

interface ToolbarProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  videoKey?: string;
  onSeekToStart: () => void;
  onSeekToEnd: () => void;
  showAllBoundingBoxes: boolean;
  setShowAllBoundingBoxes: (v: boolean) => void;
  showPlayerBoundingBox: boolean;
  setShowPlayerBoundingBox: (v: boolean) => void;
  showAllPoses: boolean;
  setShowAllPoses: (v: boolean) => void;
  showPlayerPose: boolean;
  setShowPlayerPose: (v: boolean) => void;
  trackPlayer: boolean;
  setTrackPlayer: (v: boolean) => void;
  loopPlayer: boolean;
  setLoopPlayer: (v: boolean) => void;
  showPucks: boolean;
  setShowPucks: (v: boolean) => void;
  puckConfThreshold: number;
  setPuckConfThreshold: (v: number) => void;
  cropSize: number;
  setCropSize: (v: number) => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  videoRef,
  videoKey,
  onSeekToStart,
  onSeekToEnd,
  showAllBoundingBoxes,
  setShowAllBoundingBoxes,
  showPlayerBoundingBox,
  setShowPlayerBoundingBox,
  showAllPoses,
  setShowAllPoses,
  showPlayerPose,
  setShowPlayerPose,
  trackPlayer,
  setTrackPlayer,
  loopPlayer,
  setLoopPlayer,
  showPucks,
  setShowPucks,
  puckConfThreshold,
  setPuckConfThreshold,
  cropSize,
  setCropSize,
}) => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    let video: HTMLVideoElement | null = null;
    let animationId: number;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    const updateTime = () => {
      if (video) {
        setCurrentTime(video.currentTime);
        setDuration(video.duration || 0);
      }
      animationId = requestAnimationFrame(updateTime);
    };

    const attachListeners = () => {
      video = videoRef.current;
      if (video) {
        setIsPlaying(!video.paused);
        video.addEventListener('play', handlePlay);
        video.addEventListener('pause', handlePause);
        animationId = requestAnimationFrame(updateTime);
      } else {
        setTimeout(attachListeners, 100);
      }
    };

    attachListeners();

    return () => {
      cancelAnimationFrame(animationId);
      if (video) {
        video.removeEventListener('play', handlePlay);
        video.removeEventListener('pause', handlePause);
      }
    };
  }, [videoRef, videoKey]);

  const togglePlay = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  };

  const formatTime = (timeInSeconds: number) => {
    if (isNaN(timeInSeconds)) return "00:00";
    const m = Math.floor(timeInSeconds / 60).toString().padStart(2, '0');
    const s = Math.floor(timeInSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="min-h-20 bg-slate-900 border-t border-slate-700 flex flex-wrap items-center px-4 py-2 gap-y-4 justify-between text-slate-200 shrink-0">
      <div className="flex flex-wrap items-center gap-2 shrink-0">
        <button 
          onClick={onSeekToStart}
          title="Go to start of player's sequence"
          className="p-2 hover:bg-slate-700 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-300 hover:text-white"
        >
          {/* Skip Back Icon */}
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
        </button>
        
        <button 
          onClick={togglePlay}
          className="p-2 hover:bg-slate-700 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-300 hover:text-white"
        >
          {isPlaying ? (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
          ) : (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
          )}
        </button>

        <button 
          onClick={onSeekToEnd}
          title="Go to end of player's sequence"
          className="p-2 hover:bg-slate-700 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-300 hover:text-white"
        >
          {/* Skip Forward Icon */}
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
        </button>

        <span className="text-sm font-mono text-slate-400 w-24 ml-2">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
        
        <div className="h-6 w-px bg-slate-700 mx-2"></div>
        
        <label className="flex items-center gap-2 cursor-pointer text-sm font-medium hover:text-white transition-colors">
          <input 
            type="checkbox" 
            className="rounded border-slate-600 text-purple-500 focus:ring-purple-600 bg-slate-800"
            checked={loopPlayer}
            onChange={(e) => setLoopPlayer(e.target.checked)}
          />
          Watch Player
        </label>
      </div>

      <div className="flex items-center gap-6 overflow-x-auto">
        <div className="flex flex-col gap-1 shrink-0">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-blue-500 focus:ring-blue-600 bg-slate-800"
              checked={showPlayerBoundingBox}
              onChange={(e) => setShowPlayerBoundingBox(e.target.checked)}
            />
            Player Box
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-blue-500 focus:ring-blue-600 bg-slate-800"
              checked={showAllBoundingBoxes}
              onChange={(e) => setShowAllBoundingBoxes(e.target.checked)}
            />
            All Boxes
          </label>
        </div>
        
        <div className="flex flex-col gap-1 shrink-0">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-green-500 focus:ring-green-600 bg-slate-800"
              checked={showPlayerPose}
              onChange={(e) => setShowPlayerPose(e.target.checked)}
            />
            Player Pose
          </label>
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-green-500 focus:ring-green-600 bg-slate-800"
              checked={showAllPoses}
              onChange={(e) => setShowAllPoses(e.target.checked)}
            />
            All Poses
          </label>
        </div>
        
        <div className="flex flex-col gap-1 shrink-0">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-400 hover:text-slate-200">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-amber-500 focus:ring-amber-600 bg-slate-800"
              checked={showPucks}
              onChange={(e) => setShowPucks(e.target.checked)}
            />
            Puck
          </label>
          {showPucks && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span>Conf:</span>
              <input 
                type="range" 
                min="0" 
                max="1" 
                step="0.05"
                value={puckConfThreshold}
                onChange={(e) => setPuckConfThreshold(Number(e.target.value))}
                className="w-16"
              />
              <span className="font-mono w-8 text-right">{puckConfThreshold.toFixed(2)}</span>
            </div>
          )}
        </div>

        <div className="h-8 w-px bg-slate-700 shrink-0"></div>

        <div className="flex items-center gap-4 shrink-0">
          <label className="flex items-center gap-2 cursor-pointer text-sm font-medium hover:text-white transition-colors">
            <input 
              type="checkbox" 
              className="rounded border-slate-600 text-blue-500 focus:ring-blue-600 bg-slate-800"
              checked={trackPlayer}
              onChange={(e) => setTrackPlayer(e.target.checked)}
            />
            Track Player
          </label>

          {trackPlayer && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-slate-400">Crop Size:</span>
              <input 
                type="range" 
                min="200" 
                max="1000" 
                step="50"
                value={cropSize}
                onChange={(e) => setCropSize(Number(e.target.value))}
                className="w-24"
              />
              <span className="text-xs font-mono w-10 text-right">{cropSize}px</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
