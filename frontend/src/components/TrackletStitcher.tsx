import React, { useState, useMemo } from 'react';
import type { RosterPlayer } from '../api';
import type { FrameData, Player } from '../App';

interface TrackletStitcherProps {
  roster: RosterPlayer[];
  assignments: Record<string, string>;
  ignoredTracks: number[];
  players: Player[]; // Extracted from trackingData (has id, firstFrame, lastFrame)
  trackingData: FrameData[];
  onClose: () => void;
  onUpdate: (newRoster: RosterPlayer[], newAssignments: Record<string, string>, newIgnored: number[]) => void;
  onSelectPlayer?: (p: Player) => void;
}

const getLocationZone = (realX?: number, realY?: number) => {
  if (realX === undefined || realY === undefined) return "Unknown Location";
  let xZone = "Neutral Zone";
  if (realX < -33) xZone = "Left Zone";
  if (realX > 33) xZone = "Right Zone";
  
  let yZone = "Center";
  if (realY < 28) yZone = "Top Boards";
  if (realY > 57) yZone = "Bottom Boards";
  return `${xZone} (${yZone})`;
};

export const TrackletStitcher: React.FC<TrackletStitcherProps> = ({
  roster, assignments, ignoredTracks, players, trackingData, onClose, onUpdate, onSelectPlayer
}) => {
  const [localRoster, setLocalRoster] = useState<RosterPlayer[]>(roster);
  const [localAssignments, setLocalAssignments] = useState<Record<string, string>>(assignments);
  const [localIgnored, setLocalIgnored] = useState<number[]>(ignoredTracks);
  const [draggingPlayerId, setDraggingPlayerId] = useState<string | null>(null);

  React.useEffect(() => {
    setLocalRoster(roster);
    setLocalAssignments(assignments);
    setLocalIgnored(ignoredTracks);
  }, [roster, assignments, ignoredTracks]);

  // Compute max frame for scale
  const maxFrame = useMemo(() => {
    return players.reduce((max, p) => Math.max(max, p.lastFrame), 0);
  }, [players]);

  const handleDragStart = (e: React.DragEvent, playerId: string) => {
    e.dataTransfer.setData('text/plain', playerId);
    setDraggingPlayerId(playerId);
  };

  const handleDragEnd = () => {
    setDraggingPlayerId(null);
  };

  const handleDropToRoster = (e: React.DragEvent, targetRosterId: string) => {
    e.preventDefault();
    const draggedPlayerId = e.dataTransfer.getData('text/plain');
    if (draggedPlayerId) {
      // Merge: Update assignment of dragged player to the target roster id
      const newAssignments = { ...localAssignments, [draggedPlayerId]: targetRosterId };
      setLocalAssignments(newAssignments);
      onUpdate(localRoster, newAssignments, localIgnored);
    }
  };

  const handleDropToTrash = (e: React.DragEvent) => {
    e.preventDefault();
    const draggedPlayerId = e.dataTransfer.getData('text/plain');
    if (draggedPlayerId) {
      const pid = parseInt(draggedPlayerId, 10);
      if (!localIgnored.includes(pid)) {
        const newIgnored = [...localIgnored, pid];
        setLocalIgnored(newIgnored);
        onUpdate(localRoster, localAssignments, newIgnored);
      }
    }
  };

  // Check temporal overlap
  const checkOverlap = (targetRosterId: string, draggedPlayerId: string | null): boolean => {
    if (!draggedPlayerId) return false;
    const draggedPlayer = players.find(p => p.id.toString() === draggedPlayerId);
    if (!draggedPlayer) return false;

    // Find all tracklets currently assigned to this roster ID
    const assignedIds = Object.keys(localAssignments).filter(k => localAssignments[k] === targetRosterId && k !== draggedPlayerId);
    
    // Check if draggedPlayer's frames overlap with any assigned tracklet
    for (const aId of assignedIds) {
      const assignedPlayer = players.find(p => p.id.toString() === aId);
      if (assignedPlayer) {
        if (draggedPlayer.firstFrame <= assignedPlayer.lastFrame && draggedPlayer.lastFrame >= assignedPlayer.firstFrame) {
          return true; // Overlap!
        }
      }
    }
    return false;
  };

  const updateRosterName = (id: string, name: string) => {
    const updated = localRoster.map(r => r.id === id ? { ...r, name } : r);
    setLocalRoster(updated);
    onUpdate(updated, localAssignments, localIgnored);
  };

  // Group raw players by their assigned roster profile
  const rosterGroups = localRoster.map(r => {
    const assignedPlayerIds = Object.keys(localAssignments).filter(k => localAssignments[k] === r.id);
    const assignedPlayers = players.filter(p => assignedPlayerIds.includes(p.id.toString()));
    return { rosterProfile: r, assignedPlayers };
  }).filter(group => group.assignedPlayers.length > 0); // Hide empty auto-populated profiles

  return (
    <div className="fixed inset-0 bg-slate-900/95 z-50 flex flex-col p-8 overflow-hidden text-slate-200">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-blue-400">Tracklet Stitcher</h1>
        <button onClick={onClose} className="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded font-bold">Done</button>
      </div>
      
      <div className="flex-1 overflow-y-auto mb-4 border border-slate-700 rounded-lg bg-slate-800 p-4">
        {rosterGroups.map(group => {
          const isOverlapping = checkOverlap(group.rosterProfile.id, draggingPlayerId);
          return (
            <div 
              key={group.rosterProfile.id} 
              className={`flex mb-2 p-2 rounded items-center ${isOverlapping ? 'bg-red-900/50' : 'hover:bg-slate-700 bg-slate-800/50'}`}
              onDragOver={(e) => { e.preventDefault(); if (isOverlapping) e.dataTransfer.dropEffect = 'none'; }}
              onDrop={(e) => !isOverlapping && handleDropToRoster(e, group.rosterProfile.id)}
            >
              <div className="w-48 shrink-0 flex items-center gap-2 border-r border-slate-600 mr-4 pr-2">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: group.rosterProfile.color }}></div>
                <input 
                  className="bg-transparent border-b border-transparent hover:border-slate-500 focus:border-blue-400 outline-none w-full"
                  value={group.rosterProfile.name}
                  onChange={(e) => updateRosterName(group.rosterProfile.id, e.target.value)}
                />
              </div>
              <div className="flex-1 relative h-8 bg-slate-900/50 rounded overflow-hidden">
                {group.assignedPlayers.map(p => {
                  const left = (p.firstFrame / maxFrame) * 100;
                  const width = Math.max(0.5, ((p.lastFrame - p.firstFrame) / maxFrame) * 100);
                  const isIgnored = localIgnored.includes(p.id);
                  if (isIgnored) return null;

                  const startFrameData = trackingData.find(f => f.frame === p.firstFrame);
                  const endFrameData = trackingData.find(f => f.frame === p.lastFrame);
                  const startTrack = startFrameData?.players.find(x => x.id === p.id);
                  const endTrack = endFrameData?.players.find(x => x.id === p.id);

                  const startLoc = getLocationZone(startTrack?.real_x, startTrack?.real_y);
                  const endLoc = getLocationZone(endTrack?.real_x, endTrack?.real_y);
                  const durationSec = ((p.lastFrame - p.firstFrame) / 30).toFixed(1);

                  const tooltipText = `Track ${p.id}\nTime: ${durationSec}s (Frames ${p.firstFrame}-${p.lastFrame})\nStart: ${startLoc}\nEnd: ${endLoc}\n\n[Click to seek video]`;

                  return (
                    <div 
                      key={p.id}
                      draggable
                      onClick={() => onSelectPlayer && onSelectPlayer(p)}
                      onDragStart={(e) => handleDragStart(e, p.id.toString())}
                      onDragEnd={handleDragEnd}
                      className="absolute top-1 bottom-1 bg-blue-500 rounded text-xs px-1 whitespace-nowrap overflow-hidden cursor-move border border-blue-400 shadow flex items-center hover:ring-2 hover:ring-white transition-shadow"
                      style={{ left: `${left}%`, width: `${width}%`, backgroundColor: group.rosterProfile.color }}
                      title={tooltipText}
                    >
                      <span className="font-bold mr-1">{p.id}</span>
                      {width > 15 && <span className="opacity-75 text-[10px] hidden md:inline truncate">{startLoc}</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div 
        className="h-24 bg-slate-800 border-2 border-dashed border-slate-600 flex items-center justify-center text-slate-400 rounded-lg hover:border-red-500 hover:text-red-400 transition-colors"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDropToTrash}
      >
        <div className="text-xl font-bold">🗑️ Drag tracks here to ignore/trash</div>
      </div>
    </div>
  );
};
