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
        const frameData = trackingData.find(d => d.frame === frameIndex) || trackingData[0];
        setCurrentFrameData(frameData);
      }
      animationId = requestAnimationFrame(syncFrame);
    };
    animationId = requestAnimationFrame(syncFrame);
    return () => cancelAnimationFrame(animationId);
  }, [trackingData, fps, videoRef]);

  // Standard Rink: 85 ft wide, 200 ft long.
  // The calibrated neutral zone is 85x50, starting at Y=75 on the full rink.
  const RINK_WIDTH = 85;
  const RINK_HEIGHT = 200;
  const NEUTRAL_ZONE_OFFSET_Y = 75;

  return (
    <div className="p-4 border-t border-slate-700 bg-slate-800 flex flex-col items-center">
      <h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-3 w-full">Live Tracker</h3>
      <div 
        className="relative bg-white rounded-3xl overflow-hidden shadow-inner"
        style={{ width: '180px', height: `${180 * (RINK_HEIGHT/RINK_WIDTH)}px` }}
      >
        <svg 
          viewBox={`0 0 ${RINK_WIDTH} ${RINK_HEIGHT}`} 
          className="w-full h-full pointer-events-none"
        >
          {/* Ice Surface */}
          <rect x="0" y="0" width={RINK_WIDTH} height={RINK_HEIGHT} fill="#f8fafc" />
          
          {/* Center Red Line */}
          <line x1="0" y1="100" x2={RINK_WIDTH} y2="100" stroke="#ef4444" strokeWidth="1" />
          {/* Center Circle */}
          <circle cx={RINK_WIDTH/2} cy="100" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
          
          {/* Blue Lines */}
          <line x1="0" y1="75" x2={RINK_WIDTH} y2="75" stroke="#3b82f6" strokeWidth="1" />
          <line x1="0" y1="125" x2={RINK_WIDTH} y2="125" stroke="#3b82f6" strokeWidth="1" />
          
          {/* Goal Lines */}
          <line x1="11" y1="11" x2="74" y2="11" stroke="#ef4444" strokeWidth="0.5" />
          <line x1="11" y1="189" x2="74" y2="189" stroke="#ef4444" strokeWidth="0.5" />
          
          {/* Creases */}
          <path d="M 38.5 11 A 4 4 0 0 0 46.5 11" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />
          <path d="M 38.5 189 A 4 4 0 0 1 46.5 189" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />
          
          {/* Dots representing players */}
          {currentFrameData?.players.map(player => {
            if (player.real_x === undefined || player.real_y === undefined) return null;
            
            // Map the neutral zone coordinates (0-85, 0-50) onto the full rink
            const mappedX = player.real_x;
            const mappedY = player.real_y + NEUTRAL_ZONE_OFFSET_Y;
            
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
             const mappedX = puck.real_x;
             const mappedY = puck.real_y + NEUTRAL_ZONE_OFFSET_Y;
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
        </svg>
      </div>
    </div>
  );
};
