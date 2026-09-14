import React, { useEffect, useState } from 'react';
import type { RefObject } from 'react';
import type { FrameData } from '../App';

interface MiniMapProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  trackingData: FrameData[];
  fps: number;
  selectedPlayerId?: number;
}

export const MiniMap: React.FC<MiniMapProps> = ({
  videoRef,
  trackingData,
  fps,
  selectedPlayerId
}) => {
  const [currentFrameData, setCurrentFrameData] = useState<FrameData | null>(null);

  // Sync to video time
  useEffect(() => {
    let animationId: number;
    const syncFrame = () => {
      if (videoRef.current && trackingData.length > 0) {
        const time = videoRef.current.currentTime;
        const frameIndex = Math.floor(time * fps);
        
        // Fast O(1) lookup since the array is ordered by frame
        let frameData = trackingData[frameIndex];
        
        // Fallback search if the video time exceeds the array or frames are dropped
        if (!frameData || frameData.frame !== frameIndex) {
            frameData = trackingData.find(d => Math.abs(d.frame - frameIndex) <= 1) || trackingData[0];
        }

        if (frameData) {
          setCurrentFrameData(frameData);
        }
      }
      animationId = requestAnimationFrame(syncFrame);
    };
    animationId = requestAnimationFrame(syncFrame);
    return () => cancelAnimationFrame(animationId);
  }, [trackingData, fps, videoRef]);

  // Standard Rink transposed: 200 ft long (X), 85 ft wide (Y).
  // The calibrated neutral zone is 85x50, starting at X=75 on the full rink.
  const RINK_WIDTH = 200;
  const RINK_HEIGHT = 85;
  const NEUTRAL_ZONE_OFFSET_X = 75;

  return (
    <div className="p-2 pb-4 border-t border-slate-700 bg-slate-800 flex flex-col items-center">
      <h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2 w-full">Live Tracker</h3>
      <div 
        className="relative flex justify-center items-center"
        style={{ width: '100%', maxWidth: '500px', height: '140px' }} // Adjusted styling for tighter horizontal view
      >
        <svg 
          viewBox={`0 0 ${RINK_WIDTH} ${RINK_HEIGHT}`} 
          className="w-full h-full pointer-events-none"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <clipPath id="rink-clip">
              <rect x="0" y="0" width={RINK_WIDTH} height={RINK_HEIGHT} rx="28" ry="28" />
            </clipPath>
          </defs>

          {/* Ice Surface */}
          <rect x="0" y="0" width={RINK_WIDTH} height={RINK_HEIGHT} rx="28" ry="28" fill="#f8fafc" stroke="#94a3b8" strokeWidth="1" />
          
          <g clipPath="url(#rink-clip)">
            {/* Center Red Line */}
            <line x1="100" y1="0" x2="100" y2={RINK_HEIGHT} stroke="#ef4444" strokeWidth="1" />
            {/* Center Circle & Dot */}
            <circle cx="100" cy={RINK_HEIGHT/2} r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="100" cy={RINK_HEIGHT/2} r="0.5" fill="#ef4444" />
            
            {/* Blue Lines */}
            <line x1="75" y1="0" x2="75" y2={RINK_HEIGHT} stroke="#3b82f6" strokeWidth="1" />
            <line x1="125" y1="0" x2="125" y2={RINK_HEIGHT} stroke="#3b82f6" strokeWidth="1" />
            
            {/* Goal Lines */}
            <line x1="11" y1="0" x2="11" y2={RINK_HEIGHT} stroke="#ef4444" strokeWidth="0.5" />
            <line x1="189" y1="0" x2="189" y2={RINK_HEIGHT} stroke="#ef4444" strokeWidth="0.5" />
            
            {/* Creases */}
            {/* Left crease at x=11, spanning y=38.5 to 46.5 */}
            <path d="M 11 38.5 A 4 4 0 0 1 11 46.5" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />
            {/* Right crease at x=189, spanning y=38.5 to 46.5 */}
            <path d="M 189 38.5 A 4 4 0 0 0 189 46.5" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />

            {/* End Zone Faceoff Circles */}
            <circle cx="31" cy="20.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="31" cy="64.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="169" cy="20.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="169" cy="64.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />

            {/* End Zone Faceoff Dots */}
            <circle cx="31" cy="20.5" r="1" fill="#ef4444" />
            <circle cx="31" cy="64.5" r="1" fill="#ef4444" />
            <circle cx="169" cy="20.5" r="1" fill="#ef4444" />
            <circle cx="169" cy="64.5" r="1" fill="#ef4444" />

            {/* Neutral Zone Faceoff Dots */}
            <circle cx="80" cy="20.5" r="1" fill="#ef4444" />
            <circle cx="80" cy="64.5" r="1" fill="#ef4444" />
            <circle cx="120" cy="20.5" r="1" fill="#ef4444" />
            <circle cx="120" cy="64.5" r="1" fill="#ef4444" />
          </g>
          
          {/* Dots representing players */}
          {currentFrameData?.players.map(player => {
            if (player.real_x === undefined || player.real_y === undefined) return null;
            
            // Transpose mapping:
            // Length maps to X across the SVG.
            // Width maps to Y down the SVG.
            const mappedX = player.real_x + NEUTRAL_ZONE_OFFSET_X;
            const mappedY = player.real_y;
            
            const isSelected = player.id === selectedPlayerId;
            const isPossessing = player.has_puck;
            
            let color = "#22c55e"; // Default green
            if (isSelected) color = "#ef4444"; // Selected red
            if (isPossessing && !isSelected) color = "#eab308"; // Possessing yellow
            
            return (
              <circle 
                key={player.id}
                cx={mappedX} 
                cy={mappedY} 
                r={isSelected ? "3" : "2"}
                fill={color}
                stroke="#fff"
                strokeWidth="0.5"
              />
            );
          })}
          
          {/* Pucks */}
          {currentFrameData?.entities?.filter(e => e.type === 'puck').map((puck, idx) => {
             if (puck.real_x === undefined || puck.real_y === undefined) return null;
             const mappedX = puck.real_x + NEUTRAL_ZONE_OFFSET_X;
             const mappedY = puck.real_y;
             return (
               <circle 
                 key={`puck-${idx}`}
                 cx={mappedX} 
                 cy={mappedY} 
                 r="1.5"
                 fill="#000000"
               />
             );
          })}
          
          {/* Fallback Warning if no homography/spatial data exists in this frame */}
          {(currentFrameData?.players.length ?? 0) > 0 && currentFrameData?.players.every(p => p.real_x === undefined) && (
            <text x="100" y="42.5" textAnchor="middle" fontSize="6" fill="#94a3b8" className="font-mono">
              NO SPATIAL DATA
            </text>
          )}
        </svg>
      </div>
    </div>
  );
};
