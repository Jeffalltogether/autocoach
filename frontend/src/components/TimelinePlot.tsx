import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import type { FrameData } from '../App';

interface TimelinePlotProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  trackingData: FrameData[];
  selectedPlayerId?: number;
  fps: number;
  onSeek: (time: number) => void;
}

export const TimelinePlot: React.FC<TimelinePlotProps> = ({ videoRef, trackingData, selectedPlayerId, fps, onSeek }) => {
  const playheadRef = useRef<HTMLDivElement>(null);
  const plotPoints: { x: number, y: number, time: number }[] = [];
  const possessionSpans: { startFrame: number, endFrame: number }[] = [];
  
  if (selectedPlayerId && trackingData.length > 0) {
    let lastX = 0;
    let isPossessing = false;
    let possessStart = 0;

    trackingData.forEach((frame, idx) => {
      const p = frame.players.find(pl => pl.id === selectedPlayerId);
      if (p) {
        // Chart Velocity
        if (p.velocity_mph !== undefined) {
          // Cap at 30 MPH for charting, scale to 0-100%
          plotPoints.push({ x: frame.frame, y: Math.min(100, (p.velocity_mph / 30) * 100), time: frame.frame / fps });
        } else if (idx > 0) {
          // Fallback to pixel velocity
          const velocity = Math.abs(p.x - lastX);
          plotPoints.push({ x: frame.frame, y: Math.min(100, velocity * 2), time: frame.frame / fps });
        }
        lastX = p.x;

        // Chart Possession
        if (p.has_puck && !isPossessing) {
          isPossessing = true;
          possessStart = frame.frame;
        } else if (!p.has_puck && isPossessing) {
          isPossessing = false;
          possessionSpans.push({ startFrame: possessStart, endFrame: frame.frame });
        }
      }
    });

    if (isPossessing) {
      possessionSpans.push({ startFrame: possessStart, endFrame: trackingData[trackingData.length - 1].frame });
    }
  }

  const maxFrame = trackingData.length > 0 ? trackingData[trackingData.length - 1].frame : 100;
  
  let pathD = "M0,100";
  if (plotPoints.length > 0) {
    pathD = `M${(plotPoints[0].x / maxFrame) * 100},${100 - plotPoints[0].y}`;
    plotPoints.forEach(pt => {
      pathD += ` L${(pt.x / maxFrame) * 100},${100 - pt.y}`;
    });
    pathD += ` L${(plotPoints[plotPoints.length - 1].x / maxFrame) * 100},100 Z`;
  }

  const handlePlotClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const targetFrame = Math.floor(percent * maxFrame);
    onSeek(targetFrame / fps);
  };

  // Sync playhead with video time
  useEffect(() => {
    let animationId: number;
    const updatePlayhead = () => {
      if (videoRef.current && playheadRef.current && maxFrame > 0) {
        const time = videoRef.current.currentTime;
        const totalDuration = maxFrame / fps;
        let percent = (time / totalDuration) * 100;
        percent = Math.max(0, Math.min(100, percent));
        playheadRef.current.style.left = `${percent}%`;
      }
      animationId = requestAnimationFrame(updatePlayhead);
    };
    animationId = requestAnimationFrame(updatePlayhead);
    return () => cancelAnimationFrame(animationId);
  }, [videoRef, maxFrame, fps]);

  return (
    <div className="h-32 bg-slate-800 border-t border-slate-700 p-4 flex flex-col shrink-0">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
          Player #{selectedPlayerId || '?'} Action Timeline
        </h3>
        <div className="flex gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>Velocity</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span>Contact</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span>Shot</span>
        </div>
      </div>
      
      {/* Plot Area */}
      <div 
        className="flex-1 bg-slate-900 rounded border border-slate-700 relative overflow-hidden flex items-end cursor-pointer hover:border-slate-500 transition-colors"
        onClick={handlePlotClick}
      >
        {plotPoints.length > 0 ? (
          <svg className="absolute inset-0 w-full h-full preserve-3d opacity-50" preserveAspectRatio="none" viewBox="0 0 100 100">
            {/* Draw Possession Spans as background blocks */}
            {possessionSpans.map((span, idx) => {
              const startX = (span.startFrame / maxFrame) * 100;
              const width = ((span.endFrame - span.startFrame) / maxFrame) * 100;
              return (
                <rect 
                  key={`possess-${idx}`}
                  x={startX} 
                  y="0" 
                  width={Math.max(0.5, width)} 
                  height="100" 
                  fill="rgba(250, 204, 21, 0.3)" // Yellow overlay for puck possession
                />
              );
            })}
            
            {/* Draw Velocity Line */}
            <path d={pathD} fill="rgba(59, 130, 246, 0.2)" stroke="#3b82f6" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          </svg>
        ) : (
           <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
             <span className="text-slate-600 font-mono text-sm">[ No Data for Player ]</span>
           </div>
        )}
        
        {/* Playhead Scrubber Line */}
        <div 
          ref={playheadRef}
          className="absolute top-0 bottom-0 w-px bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)] z-10 flex flex-col items-center pointer-events-none"
          style={{ left: '0%' }}
        >
          <div className="w-3 h-3 bg-white rounded-full -mt-1.5 shadow"></div>
        </div>
      </div>
    </div>
  );
};
