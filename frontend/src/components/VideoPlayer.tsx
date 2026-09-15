import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { FrameData } from '../App';

interface VideoPlayerProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  videoUrl: string;
  trackingData: FrameData[];
  selectedPlayerId?: number;
  selectedPlayerFirstFrame?: number;
  selectedPlayerLastFrame?: number;
  showAllBoundingBoxes: boolean;
  showPlayerBoundingBox: boolean;
  showAllPoses: boolean;
  showPlayerPose: boolean;
  trackPlayer: boolean;
  loopPlayer: boolean;
  showPucks: boolean;
  puckConfThreshold: number;
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
  videoUrl,
  trackingData,
  selectedPlayerId,
  selectedPlayerFirstFrame,
  selectedPlayerLastFrame,
  showAllBoundingBoxes,
  showPlayerBoundingBox,
  showAllPoses,
  showPlayerPose,
  trackPlayer,
  loopPlayer,
  showPucks,
  puckConfThreshold,
  cropSize,
  fps
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentFrameData, setCurrentFrameData] = useState<FrameData | null>(null);
  const [videoDimensions, setVideoDimensions] = useState({ width: 1920, height: 1080 });
  const [lastOrigin, setLastOrigin] = useState('50% 50%');

  useEffect(() => {
    let animationId: number;

    const syncFrame = () => {
      if (videoRef.current && trackingData.length > 0) {
        const time = videoRef.current.currentTime;
        // Use Math.round to avoid floating point precision issues causing infinite loops when clamping
        const frameIndex = Math.round(time * fps);
        const frameData = trackingData.find(d => d.frame === frameIndex) || trackingData[0];
        setCurrentFrameData(frameData);

        // Watch Player Sequence Logic
        if (loopPlayer && selectedPlayerId && selectedPlayerFirstFrame !== undefined && selectedPlayerLastFrame !== undefined) {
          if (frameIndex >= selectedPlayerLastFrame) {
            if (!videoRef.current.paused) {
              videoRef.current.pause();
            }
            // Clamp to exact last frame so it doesn't overshoot
            videoRef.current.currentTime = selectedPlayerLastFrame / fps;
          } else if (frameIndex < selectedPlayerFirstFrame) {
            // If they seek backwards out of bounds, snap them to the start of the sequence
            videoRef.current.currentTime = selectedPlayerFirstFrame / fps;
          }
        }
      }
      animationId = requestAnimationFrame(syncFrame);
    };
    
    animationId = requestAnimationFrame(syncFrame);
    return () => cancelAnimationFrame(animationId);
  }, [trackingData, fps, videoRef, loopPlayer, selectedPlayerId, selectedPlayerFirstFrame, selectedPlayerLastFrame]);

  const handleVideoLoad = () => {
    if (videoRef.current) {
      setVideoDimensions({
        width: videoRef.current.videoWidth,
        height: videoRef.current.videoHeight
      });
    }
  };

  const trackedPlayer = currentFrameData?.players.find(p => p.id === selectedPlayerId);

  // Keep track of the player's last known position so we can zoom in smoothly even if they toggle tracking while the player is on screen
  useEffect(() => {
    if (trackedPlayer) {
      const px = trackedPlayer.x / videoDimensions.width;
      const py = trackedPlayer.y / videoDimensions.height;
      setLastOrigin(`${px * 100}% ${py * 100}%`);
    }
  }, [trackedPlayer, videoDimensions]);

  let transformStyle = {};
  if (trackPlayer && containerRef.current) {
    const scale = Math.max(1, containerRef.current.clientWidth / cropSize);
    transformStyle = {
      transform: `scale(${scale})`,
      transformOrigin: lastOrigin,
      transition: 'transform-origin 0.1s linear, transform 0.3s ease',
    };
  } else {
    transformStyle = {
      transform: 'scale(1)',
      transformOrigin: lastOrigin,
      transition: 'transform-origin 0.1s linear, transform 0.3s ease',
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
        <video key={videoUrl} 
          ref={videoRef}
          src={videoUrl} 
          className="absolute max-w-full max-h-full"
          style={{ width: videoDimensions.width, height: videoDimensions.height, objectFit: 'contain' }}
          controls={false}
          autoPlay muted playsInline loop={!loopPlayer} // Only use standard HTML5 loop if we aren't enforcing a player loop
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
            {(showAllPoses || showPlayerPose) && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none z-20" viewBox={`0 0 ${videoDimensions.width} ${videoDimensions.height}`}>
                {currentFrameData.players.map((player) => {
                  const isSelected = player.id === selectedPlayerId;
                  if (!showAllPoses && (!isSelected || !showPlayerPose)) return null;

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
                              stroke={isSelected ? "#ef4444" : "#4ade80"} 
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
                              fill={isSelected ? "#dc2626" : "#22c55e"} 
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
            {(showAllBoundingBoxes || showPlayerBoundingBox) && currentFrameData.players.map((player) => {
              const isSelected = player.id === selectedPlayerId;
              if (!showAllBoundingBoxes && (!isSelected || !showPlayerBoundingBox)) return null;

              const top = player.y - player.height / 2;
              const left = player.x - player.width / 2;
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

            {/* Draw Puck Bounding Boxes */}
            {showPucks && currentFrameData.entities?.filter(e => e.type === 'puck' && (e.conf ?? 1) >= puckConfThreshold).map((puck, idx) => {
              const top = puck.y - puck.height / 2;
              const left = puck.x - puck.width / 2;
              return (
                <div 
                  key={`puck-${idx}`}
                  className="absolute border-2 border-amber-400 bg-amber-400/20 z-10"
                  style={{
                    left: `${(left / videoDimensions.width) * 100}%`,
                    top: `${(top / videoDimensions.height) * 100}%`,
                    width: `${(puck.width / videoDimensions.width) * 100}%`,
                    height: `${(puck.height / videoDimensions.height) * 100}%`,
                  }}
                >
                  <div className="absolute -top-5 left-0 text-white text-xs px-1 font-mono whitespace-nowrap bg-amber-500 rounded-sm">
                    Puck
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
