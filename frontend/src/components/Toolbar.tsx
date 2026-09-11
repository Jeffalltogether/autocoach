
interface ToolbarProps {
  showBoundingBoxes: boolean;
  setShowBoundingBoxes: (v: boolean) => void;
  showPose: boolean;
  setShowPose: (v: boolean) => void;
  trackPlayer: boolean;
  setTrackPlayer: (v: boolean) => void;
  cropSize: number;
  setCropSize: (v: number) => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  showBoundingBoxes,
  setShowBoundingBoxes,
  showPose,
  setShowPose,
  trackPlayer,
  setTrackPlayer,
  cropSize,
  setCropSize,
}) => {
  return (
    <div className="h-16 bg-slate-900 border-t border-slate-700 flex items-center px-6 justify-between text-slate-200 shrink-0">
      <div className="flex items-center gap-4">
        {/* Mock Playback Controls */}
        <button className="p-2 hover:bg-slate-700 rounded-full">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" /></svg>
        </button>
        <div className="w-64 h-2 bg-slate-700 rounded-full relative">
          <div className="absolute top-0 left-0 h-full w-1/3 bg-blue-500 rounded-full"></div>
        </div>
        <span className="text-xs font-mono text-slate-400">01:23 / 04:56</span>
      </div>

      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input 
            type="checkbox" 
            className="rounded border-slate-600 text-blue-500 focus:ring-blue-600 bg-slate-800"
            checked={showBoundingBoxes}
            onChange={(e) => setShowBoundingBoxes(e.target.checked)}
          />
          Boxes
        </label>
        
        <label className="flex items-center gap-2 cursor-pointer text-sm">
          <input 
            type="checkbox" 
            className="rounded border-slate-600 text-green-500 focus:ring-green-600 bg-slate-800"
            checked={showPose}
            onChange={(e) => setShowPose(e.target.checked)}
          />
          Pose
        </label>

        <div className="h-6 w-px bg-slate-700"></div>

        <label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
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
  );
};
