import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { FrameData } from '../App';

interface VideoPlayerProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  trackingData: FrameData[];
  selectedPlayerId?: number;
  showBoundingBoxes: boolean;
  showPose: boolean;
  trackPlayer: boolean;
  cropSize: number;
  fps: number;
}

const SKELETON = [
  [0, 1], [0, 2], [1, 3], [2, 4], 
  [5, 7], [7, 9], [6, 8], [8, 10], 
  [5, 6], [5, 11], [6, 12], [11, 12], 
  [11, 13], [13, 15], [12, 14], [14, 16]
];

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoRef,
  trackingData,
  selectedPlayerId,
  showBoundingBoxes,
  showPose,
  trackPlayer,
  cropSize,
  fps
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentFrameData, setCurrentFrameData] = useState<FrameData | null>(null);
  const [videoDimensions, setVideoDimensions] = useState({ width: 1920, height: 1080 });

  useEffect(() => {
    let animationId: number;
    const syncFrame = () => {
      if (videoRef.current && trackingData.length > 0) {
        const time = videoRef.current.currentTime;
        const frameIndex = Math.floor(time * fps);
        const frameData = trackingData.find(d => d.frame === frameIndex) || trackingData[0];
        setCurrentFrameData(frameData);
      }
      animationId = requestAnimationFrame(syncFrame);
    };
    animationId = requestAnimationFrame(syncFrame);
    return () => cancelAnimationFrame(animationId);
  }, [trackingData, fps, videoRef]);

  const handleVideoLoad = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    setVideoDimensions({ width: video.videoWidth || 1920, height: video.videoHeight || 1080 });
  };

  const trackedPlayer = currentFrameData?.players.find(p => p.id === selectedPlayerId) || currentFrameData?.players[0];

  let transformStyle = {};
  if (trackPlayer && containerRef.current && trackedPlayer) {
    const scale = Math.max(1, containerRef.current.clientWidth / cropSize);
    const px = trackedPlayer.x / videoDimensions.width;
    const py = trackedPlayer.y / videoDimensions.height;
    transformStyle = {
      transform: `scale(${scale})`,
      transformOrigin: `${px * 100}% ${py * 100}%`,
      transition: 'transform-origin 0.1s linear',
    };
  } else {
    transformStyle = {
      transform: 'scale(1)',
      transformOrigin: 'center center',
      transition: 'transform 0.3s ease',
    };
  }

  return (
    <div className="flex-1 bg-black overflow-hidden relative flex items-center justify-center" ref={containerRef}>
      <div 
        className="relative" 
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          ...transformStyle
        }}
      >
        <video 
          ref={videoRef}
          src="/video.mp4" 
          className="absolute max-w-full max-h-full"
          style={{ width: videoDimensions.width, height: videoDimensions.height, objectFit: 'contain' }}
          controls={false}
          autoPlay muted loop
          onLoadedMetadata={handleVideoLoad}
        />

        {currentFrameData && (
          <div 
            className="absolute"
            style={{ 
              width: videoDimensions.width, 
              height: videoDimensions.height,
              maxWidth: '100%',
              maxHeight: '100%',
              aspectRatio: `${videoDimensions.width}/${videoDimensions.height}`
            }}
          >
            {/* Draw Skeletons via SVG */}
            {showPose && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none z-20" viewBox={`0 0 ${videoDimensions.width} ${videoDimensions.height}`}>
                {currentFrameData.players.map((player) => {
                  if (!player.keypoints || !Array.isArray(player.keypoints) || player.keypoints.length < 17) {
                    return null;
                  }
                  
                  return (
                    <g key={`pose-${player.id}`}>
                      {/* Lines */}
                      {SKELETON.map(([i, j], idx) => {
                        const pt1 = player.keypoints![i];
                        const pt2 = player.keypoints![j];
                        if (pt1 && pt2 && pt1.conf > 0.1 && pt2.conf > 0.1) {
                          return (
                            <line 
                              key={`line-${idx}`} 
                              x1={pt1.x} y1={pt1.y} 
                              x2={pt2.x} y2={pt2.y} 
                              stroke={player.id === selectedPlayerId ? "#ef4444" : "#4ade80"} 
                              strokeWidth="8" strokeOpacity="0.9" 
                            />
                          );
                        }
                        return null;
                      })}
                      {/* Dots */}
                      {player.keypoints!.map((pt, idx) => {
                        if (pt && pt.conf > 0.1) {
                          return (
                            <circle 
                              key={`pt-${idx}`} 
                              cx={pt.x} cy={pt.y} 
                              r="8" 
                              fill={player.id === selectedPlayerId ? "#dc2626" : "#22c55e"} 
                            />
                          );
                        }
                        return null;
                      })}
                    </g>
                  );
                })}
              </svg>
            )}

            {/* Draw Bounding Boxes */}
            {showBoundingBoxes && currentFrameData.players.map((player) => {
              const top = player.y - player.height / 2;
              const left = player.x - player.width / 2;
              const isSelected = player.id === selectedPlayerId;
              return (
                <div 
                  key={`box-${player.id}`}
                  className={`absolute border-2 ${isSelected ? 'border-red-500 bg-red-500/20 z-10' : 'border-blue-500 bg-blue-500/10'}`}
                  style={{
                    left: `${(left / videoDimensions.width) * 100}%`,
                    top: `${(top / videoDimensions.height) * 100}%`,
                    width: `${(player.width / videoDimensions.width) * 100}%`,
                    height: `${(player.height / videoDimensions.height) * 100}%`,
                  }}
                >
                  <div className={`absolute -top-6 left-0 text-white text-xs px-1 font-mono whitespace-nowrap ${isSelected ? 'bg-red-500' : 'bg-blue-500'}`}>
                    Player #{player.id}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
