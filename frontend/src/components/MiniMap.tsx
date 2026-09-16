import React, { useEffect, useState, useRef } from 'react';
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
  const [showHeatmap, setShowHeatmap] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Sync to video time
  useEffect(() => {
    let animationId: number;
    const syncFrame = () => {
      if (videoRef.current && trackingData.length > 0) {
        const time = videoRef.current.currentTime;
        const frameIndex = Math.floor(time * fps);
        
        let frameData = trackingData[frameIndex];
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

  // Standard Rink transposed
  const RINK_WIDTH = 200;
  const RINK_HEIGHT = 85;
  const NEUTRAL_ZONE_OFFSET_X = 75;

  // Heatmap rendering logic
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (showHeatmap && selectedPlayerId) {
      // Dynamically scale opacity based on how many frames the player appears in
      // This prevents long videos from becoming solid red blocks, and short videos from being invisible.
      let playerFrameCount = 0;
      trackingData.forEach(frame => {
        if (frame.players.some(p => p.id === selectedPlayerId)) {
          playerFrameCount++;
        }
      });
      
      // Aim for ~40 overlapping frames to reach solid color
      const dynamicAlpha = Math.max(0.01, Math.min(0.5, 40 / (playerFrameCount || 1)));

      // Draw Heatmap
      ctx.filter = 'blur(3px)'; // reduced blur for sharper mapping
      ctx.globalAlpha = dynamicAlpha;
      ctx.fillStyle = '#000000'; // Draw in black to build alpha density

      trackingData.forEach(frame => {
        const player = frame.players.find(p => p.id === selectedPlayerId);
        if (player && player.real_x !== undefined && player.real_y !== undefined) {
          const mappedX = player.real_x + NEUTRAL_ZONE_OFFSET_X;
          const mappedY = player.real_y;
          
          ctx.beginPath();
          ctx.arc(mappedX, mappedY, 6, 0, Math.PI * 2);
          ctx.fill();
        }
      });
      
      // Reset context before reading pixels
      ctx.filter = 'none';
      ctx.globalAlpha = 1.0;
      
      // Map alpha to Jet Colormap
      const gradCanvas = document.createElement('canvas');
      gradCanvas.width = 1; gradCanvas.height = 256;
      const gctx = gradCanvas.getContext('2d');
      if (gctx) {
        const grad = gctx.createLinearGradient(0, 0, 0, 256);
        // Jet Colormap: transparent -> dark blue -> blue -> cyan -> green -> yellow -> red
        grad.addColorStop(0, 'rgba(0,0,128,0)');
        grad.addColorStop(0.1, 'rgba(0,0,255,0.2)');
        grad.addColorStop(0.3, 'rgba(0,255,255,0.5)');
        grad.addColorStop(0.5, 'rgba(0,255,0,0.7)');
        grad.addColorStop(0.7, 'rgba(255,255,0,0.8)');
        grad.addColorStop(1, 'rgba(255,0,0,1)');
        gctx.fillStyle = grad;
        gctx.fillRect(0, 0, 1, 256);
        const colormap = gctx.getImageData(0, 0, 1, 256).data;
        
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imgData.data;
        for (let i = 0; i < pixels.length; i += 4) {
          const a = pixels[i + 3]; // Alpha channel is our density
          if (a > 0) {
            const cIdx = a * 4;
            pixels[i] = colormap[cIdx];         // R
            pixels[i+1] = colormap[cIdx + 1];   // G
            pixels[i+2] = colormap[cIdx + 2];   // B
            pixels[i+3] = colormap[cIdx + 3];   // A
          }
        }
        ctx.putImageData(imgData, 0, 0);
      }
    }
  }, [showHeatmap, selectedPlayerId, trackingData]);

  return (
    <div className="p-2 pb-4 border-t border-slate-700 bg-slate-800 flex flex-col items-center flex-1">
      <div className="flex justify-between items-center w-full mb-2">
        <h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Live Tracker</h3>
        <button 
          onClick={() => setShowHeatmap(!showHeatmap)}
          disabled={!selectedPlayerId}
          className={`text-xs px-2 py-1 rounded transition-colors ${
            !selectedPlayerId ? 'opacity-50 cursor-not-allowed bg-slate-700 text-slate-500' :
            showHeatmap ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          {showHeatmap ? 'Heatmap: ON' : 'Heatmap: OFF'}
        </button>
      </div>
      
      <div 
        className="relative flex justify-center items-center w-full flex-1 min-h-0"
      >
        <canvas 
          ref={canvasRef}
          width={RINK_WIDTH}
          height={RINK_HEIGHT}
          className="absolute inset-0 w-full h-full object-contain pointer-events-none z-10"
        />

        <svg 
          viewBox={`0 0 ${RINK_WIDTH} ${RINK_HEIGHT}`} 
          className="absolute inset-0 w-full h-full object-contain pointer-events-none z-20"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <clipPath id="rink-clip">
              <rect x="0" y="0" width={RINK_WIDTH} height={RINK_HEIGHT} rx="28" ry="28" />
            </clipPath>
          </defs>

          {/* Ice Surface */}
          <rect x="0" y="0" width={RINK_WIDTH} height={RINK_HEIGHT} rx="28" ry="28" fill="#f8fafc" stroke="#94a3b8" strokeWidth="1" fillOpacity={showHeatmap ? 0.9 : 1} />
          
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
            <path d="M 11 38.5 A 4 4 0 0 1 11 46.5" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />
            <path d="M 189 38.5 A 4 4 0 0 0 189 46.5" fill="#3b82f6" fillOpacity="0.3" stroke="#ef4444" strokeWidth="0.5" />

            {/* End Zone Faceoff Circles & Dots */}
            <circle cx="31" cy="20.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="31" cy="64.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="169" cy="20.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
            <circle cx="169" cy="64.5" r="15" fill="none" stroke="#ef4444" strokeWidth="0.5" />
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
          {!showHeatmap && currentFrameData?.players.map(player => {
            if (player.real_x === undefined || player.real_y === undefined) return null;
            
            const mappedX = player.real_x + NEUTRAL_ZONE_OFFSET_X;
            const mappedY = player.real_y;
            
            const isSelected = player.id === selectedPlayerId;
            const isPossessing = player.has_puck;
            
            let color = "#22c55e"; // Default green
            if (isSelected) color = "#ef4444"; // Selected red
            if (isPossessing && !isSelected) color = "#eab308"; // Possessing yellow
            
            return (
              <g key={player.id}>
                <circle 
                  cx={mappedX} 
                  cy={mappedY} 
                  r={isSelected ? "4" : "3"}
                  fill={color}
                  stroke="#fff"
                  strokeWidth="0.5"
                />
                <text
                  x={mappedX}
                  y={mappedY + 0.5}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill="#ffffff"
                  fontSize={isSelected ? "4.5" : "3.5"}
                  fontFamily="sans-serif"
                  fontWeight="bold"
                >
                  {player.id}
                </text>
              </g>
            );
          })}

          {/* If heatmap is on, only show the selected player dot on top of heatmap */}
          {showHeatmap && selectedPlayerId && currentFrameData?.players.map(player => {
            if (player.id !== selectedPlayerId || player.real_x === undefined || player.real_y === undefined) return null;
            
            const mappedX = player.real_x + NEUTRAL_ZONE_OFFSET_X;
            const mappedY = player.real_y;
            
            return (
              <g key={player.id}>
                <circle 
                  cx={mappedX} 
                  cy={mappedY} 
                  r="4"
                  fill="#ffffff"
                  stroke="#000000"
                  strokeWidth="0.5"
                />
                <text
                  x={mappedX}
                  y={mappedY + 0.5}
                  textAnchor="middle"
                  alignmentBaseline="middle"
                  fill="#000000"
                  fontSize="4.5"
                  fontFamily="sans-serif"
                  fontWeight="bold"
                >
                  {player.id}
                </text>
              </g>
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
