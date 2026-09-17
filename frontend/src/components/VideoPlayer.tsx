import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { FrameData } from '../App';
import type { RosterPlayer } from '../api';

interface VideoPlayerProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  videoUrl: string;
  trackingData: FrameData[];
  roster: RosterPlayer[];
  assignments: Record<string, string>;
  ignoredTracks: number[];
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
  fps,
  roster,
  assignments,
  ignoredTracks
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentFrameData, setCurrentFrameData] = useState<FrameData | null>(null);
  const [videoDimensions, setVideoDimensions] = useState({ width: 1920, height: 1080 });
  const lastOriginRef = useRef('50% 50%');

  useEffect(() => {
    let animationId: number;

    const syncFrame = () => {
      if (videoRef.current && trackingData.length > 0) {
        const time = videoRef.current.currentTime;
        // Use Math.round to avoid floating point precision issues causing infinite loops when clamping
        const frameIndex = Math.round(time * fps);
        
        let frameData = trackingData[frameIndex];
        if (!frameData || frameData.frame !== frameIndex) {
            frameData = trackingData.find(d => Math.abs(d.frame - frameIndex) <= 1) || trackingData[0];
        }

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
  // Update it synchronously during render to avoid cascading re-renders that break tracking continuity
  if (trackedPlayer) {
    const px = trackedPlayer.x / videoDimensions.width;
    const py = trackedPlayer.y / videoDimensions.height;
    lastOriginRef.current = `${px * 100}% ${py * 100}%`;
  }

  let transformStyle = {};
  if (trackPlayer && containerRef.current) {
    const scale = Math.max(1, containerRef.current.clientWidth / cropSize);
    transformStyle = {
      transform: `scale(${scale})`,
      transformOrigin: lastOriginRef.current,
      transition: 'transform 0.3s ease',
    };
  } else {
    transformStyle = {
      transform: 'scale(1)',
      transformOrigin: lastOriginRef.current,
      transition: 'transform 0.3s ease',
    };
  }

  return (
    <div className="flex-1 bg-black overflow-hidden relative flex items-center justify-center" ref={containerRef}>
      <div 
        className="relative flex items-center justify-center" 
        style={{
          width: videoDimensions.width, 
          height: videoDimensions.height,
          maxWidth: '100%',
          maxHeight: '100%',
          aspectRatio: `${videoDimensions.width}/${videoDimensions.height}`,
          ...transformStyle
        }}
      >
        <video key={videoUrl} 
          ref={videoRef}
          src={videoUrl} 
          className="absolute inset-0 w-full h-full"
          style={{ objectFit: 'contain' }}
          controls={false}
          autoPlay muted playsInline loop={!loopPlayer} // Only use standard HTML5 loop if we aren't enforcing a player loop
          onLoadedMetadata={handleVideoLoad}
        />

        {currentFrameData && (
          <div className="absolute inset-0">
            {/* Draw Skeletons and Bounding Boxes via SVG */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-20" viewBox={`0 0 ${videoDimensions.width} ${videoDimensions.height}`}>
              {currentFrameData.players.map((player) => {
                if (ignoredTracks.includes(player.id)) return null;

                const isSelected = player.id === selectedPlayerId;
                const showBox = showAllBoundingBoxes || (showPlayerBoundingBox && isSelected);
                const showPose = showAllPoses || (showPlayerPose && isSelected);

                if (!showBox && !showPose) return null;

                const top = player.y - player.height / 2;
                const left = player.x - player.width / 2;

                let displayName = `Player #${player.id}`;
                let strokeColor = isSelected ? "#ef4444" : "#3b82f6";
                let fillColor = isSelected ? "rgba(239, 68, 68, 0.2)" : "rgba(59, 130, 246, 0.1)";
                
                const rosterId = assignments[player.id.toString()];
                if (rosterId) {
                  const assignedRoster = roster.find(r => r.id === rosterId);
                  if (assignedRoster) {
                    displayName = assignedRoster.name;
                    strokeColor = assignedRoster.color;
                    fillColor = isSelected ? "rgba(255, 255, 255, 0.3)" : `${assignedRoster.color}33`; // Highlight selection logic
                    if (isSelected) {
                      strokeColor = "#ffffff";
                    }
                  }
                }

                return (
                  <g key={`player-${player.id}`}>
                    {showPose && (
                      <g>
                        {/* Lines */}
                        {SKELETON.map(([i, j], idx) => {
                          const pt1 = player.keypoints?.[i];
                          const pt2 = player.keypoints?.[j];
                          if (pt1 && pt2 && pt1.conf > 0.1 && pt2.conf > 0.1) {
                            return (
                              <line 
                                key={`line-${idx}`}
                                x1={pt1.x} y1={pt1.y} 
                                x2={pt2.x} y2={pt2.y} 
                                stroke={strokeColor} 
                                strokeWidth="4" 
                              />
                            );
                          }
                          return null;
                        })}
                        {/* Points */}
                        {player.keypoints?.map((pt, idx) => {
                          if (pt.conf > 0.1) {
                            return <circle key={`pt-${idx}`} cx={pt.x} cy={pt.y} r="4" fill="#ffffff" />;
                          }
                          return null;
                        })}
                      </g>
                    )}

                    {showBox && (
                      <g>
                        <rect 
                          x={left} y={top} 
                          width={player.width} height={player.height} 
                          fill={fillColor}
                          stroke={strokeColor}
                          strokeWidth={isSelected ? "5" : "3"}
                        />
                        {/* Player ID Label */}
                        <rect 
                          x={left} y={top - 30} 
                          width={140} height={30} 
                          fill={strokeColor} 
                        />
                        <text 
                          x={left + 5} y={top - 8} 
                          fill={isSelected ? "#000000" : "#ffffff"} 
                          fontSize="22" 
                          fontFamily="sans-serif"
                          fontWeight="bold"
                        >
                          {displayName}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Draw Puck Bounding Boxes */}
              {showPucks && currentFrameData.entities?.filter(e => e.type === 'puck' && (e.conf ?? 1) >= puckConfThreshold).map((puck, idx) => {
                const top = puck.y - puck.height / 2;
                const left = puck.x - puck.width / 2;
                return (
                  <g key={`puck-${idx}`}>
                    <rect 
                      x={left} y={top} 
                      width={puck.width} height={puck.height} 
                      fill="rgba(251, 191, 36, 0.2)"
                      stroke="#fbbf24"
                      strokeWidth="4"
                    />
                    <rect 
                      x={left} y={top - 24} 
                      width={80} height={24} 
                      fill="#f59e0b" 
                    />
                    <text 
                      x={left + 5} y={top - 6} 
                      fill="#ffffff" 
                      fontSize="18" 
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      Puck
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        )}
      </div>
    </div>
  );
};
