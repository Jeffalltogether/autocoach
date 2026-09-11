import type { FrameData } from '../App';

interface TimelinePlotProps {
  trackingData: FrameData[];
  selectedPlayerId?: number;
  fps: number;
  onSeek: (time: number) => void;
}

export const TimelinePlot: React.FC<TimelinePlotProps> = ({ trackingData, selectedPlayerId, fps, onSeek }) => {
  // If we have tracking data and a selected player, let's plot their X-velocity over time (as a mock)
  const plotPoints: { x: number, y: number, time: number }[] = [];
  
  if (selectedPlayerId && trackingData.length > 0) {
    let lastX = 0;
    trackingData.forEach((frame, idx) => {
      const p = frame.players.find(pl => pl.id === selectedPlayerId);
      if (p) {
        if (idx > 0) {
          const velocity = Math.abs(p.x - lastX);
          plotPoints.push({ x: frame.frame, y: Math.min(100, velocity * 2), time: frame.frame / fps });
        }
        lastX = p.x;
      }
    });
  }

  // Simple path generator for velocity
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
            <path d={pathD} fill="rgba(59, 130, 246, 0.2)" stroke="#3b82f6" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          </svg>
        ) : (
           <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
             <span className="text-slate-600 font-mono text-sm">[ No Data for Player ]</span>
           </div>
        )}
      </div>
    </div>
  );
};
