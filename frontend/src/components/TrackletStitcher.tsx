import React, { useState, useMemo } from 'react';
import type { RosterPlayer } from '../api';
import type { FrameData, Player } from '../App';

interface TrackletStitcherProps {
  roster: RosterPlayer[];
  assignments: Record<string, string>;
  ignoredTracks: number[];
  players: Player[]; // Extracted from trackingData (has id, firstFrame, lastFrame)
  trackingData: FrameData[];
  selectedPlayerId?: number;
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
  roster, assignments, ignoredTracks, players, trackingData, selectedPlayerId, onClose, onUpdate, onSelectPlayer
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

  const handleDropToNewPlayer = (e: React.DragEvent) => {
    e.preventDefault();
    const draggedPlayerId = e.dataTransfer.getData('text/plain');
    if (draggedPlayerId) {
      const originalRosterId = `r_${draggedPlayerId}`;
      const newAssignments = { ...localAssignments, [draggedPlayerId]: originalRosterId };
      
      // Check if original roster exists
      if (!localRoster.some(r => r.id === originalRosterId)) {
        const newProfile = { id: originalRosterId, name: `Player #${draggedPlayerId}`, jersey: '', color: '#3b82f6' };
        setLocalRoster([...localRoster, newProfile]);
        onUpdate([...localRoster, newProfile], newAssignments, localIgnored);
      } else {
        setLocalAssignments(newAssignments);
        onUpdate(localRoster, newAssignments, localIgnored);
      }
    }
  };

  // Check temporal overlap against a specific roster row
  const checkOverlap = (targetRosterId: string, testPlayerId: string | null): boolean => {
    if (!testPlayerId) return false;
    const testPlayer = players.find(p => p.id.toString() === testPlayerId);
    if (!testPlayer) return false;

    // Find all tracklets currently assigned to this roster ID
    const assignedIds = Object.keys(localAssignments).filter(k => localAssignments[k] === targetRosterId && k !== testPlayerId);
    
    for (const aId of assignedIds) {
      const assignedPlayer = players.find(p => p.id.toString() === aId);
      if (assignedPlayer) {
        if (testPlayer.firstFrame <= assignedPlayer.lastFrame && testPlayer.lastFrame >= assignedPlayer.firstFrame) {
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

  // Group raw players by their assigned roster profile and sort them smartly
  const sortedRosterGroups = useMemo(() => {
    const groups = localRoster.map(r => {
      const assignedPlayerIds = Object.keys(localAssignments).filter(k => localAssignments[k] === r.id);
      const assignedPlayers = players.filter(p => assignedPlayerIds.includes(p.id.toString()));
      return { rosterProfile: r, assignedPlayers };
    }).filter(group => group.assignedPlayers.length > 0);
    
    if (!selectedPlayerId) return groups;
    
    const selectedTrack = players.find(p => p.id === selectedPlayerId);
    if (!selectedTrack) return groups;

    return groups.sort((a, b) => {
      const aHasSelected = a.assignedPlayers.some(p => p.id === selectedPlayerId);
      const bHasSelected = b.assignedPlayers.some(p => p.id === selectedPlayerId);
      
      if (aHasSelected) return -1;
      if (bHasSelected) return 1;

      const aOverlaps = checkOverlap(a.rosterProfile.id, selectedPlayerId.toString());
      const bOverlaps = checkOverlap(b.rosterProfile.id, selectedPlayerId.toString());
      
      if (aOverlaps && !bOverlaps) return 1;
      if (!aOverlaps && bOverlaps) return -1;

      // Both don't overlap, rank by shortest time gap to selectedTrack
      const getMinGap = (group: typeof a) => {
        let min = Infinity;
        group.assignedPlayers.forEach(p => {
          if (p.lastFrame < selectedTrack.firstFrame) {
            min = Math.min(min, selectedTrack.firstFrame - p.lastFrame);
          } else if (p.firstFrame > selectedTrack.lastFrame) {
            min = Math.min(min, p.firstFrame - selectedTrack.lastFrame);
          }
        });
        return min;
      };

      return getMinGap(a) - getMinGap(b);
    });
  }, [localRoster, localAssignments, players, selectedPlayerId]);

  return (
    <div className="fixed bottom-0 left-0 right-0 h-[55vh] bg-slate-900 border-t-[3px] border-blue-500 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] z-50 flex flex-col p-4 overflow-hidden text-slate-200">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold text-blue-400">Tracklet Stitcher</h1>
        <button onClick={onClose} className="bg-slate-700 hover:bg-slate-600 px-4 py-1.5 rounded font-bold text-sm">Done</button>
      </div>
      
      <div className="flex-1 overflow-y-auto mb-4 border border-slate-700 rounded-lg bg-slate-800 p-4">
        {sortedRosterGroups.map(group => {
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

      <div className="flex space-x-4 mt-2 h-20 shrink-0">
        <div 
          className="flex-1 bg-slate-800 border-2 border-dashed border-slate-600 flex items-center justify-center text-slate-400 rounded-lg hover:border-blue-500 hover:text-blue-400 transition-colors cursor-crosshair"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropToNewPlayer}
        >
          <div className="text-lg font-bold">✂️ Un-stitch (Split to new row)</div>
        </div>
        
        <div 
          className="flex-1 bg-slate-800 border-2 border-dashed border-slate-600 flex items-center justify-center text-slate-400 rounded-lg hover:border-red-500 hover:text-red-400 transition-colors cursor-crosshair"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDropToTrash}
        >
          <div className="text-lg font-bold">🗑️ Trash / Ignore Tracks</div>
        </div>
      </div>
    </div>
  );
};
