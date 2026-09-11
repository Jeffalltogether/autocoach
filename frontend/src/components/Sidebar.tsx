import type { Session } from '../App';
import type { Player, FrameData } from '../App';
import { MiniMap } from './MiniMap';
import React, { RefObject } from 'react';

interface SidebarProps {
  sessions: Session[];
  players: Player[];
  selectedSession: Session | null;
  selectedPlayer: Player | null;
  onSelectSession: (s: Session) => void;
  onSelectPlayer: (p: Player) => void;
  videoRef: RefObject<HTMLVideoElement | null>;
  trackingData: FrameData[];
  fps: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  players,
  selectedSession,
  selectedPlayer,
  onSelectSession,
  onSelectPlayer,
  videoRef,
  trackingData,
  fps
}) => {
  return (
    <div className="w-64 bg-slate-800 text-slate-100 flex flex-col h-full border-r border-slate-700">
      <div className="p-4 border-b border-slate-700">
        <h2 className="text-xl font-bold mb-4 text-blue-400">AutoCoach</h2>
        <h3 className="text-sm uppercase tracking-wider text-slate-400 font-semibold mb-2">Sessions</h3>
        <div className="flex flex-col gap-2">
          {sessions.map(session => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session)}
              className={`text-left px-3 py-2 rounded transition-colors ${
                selectedSession?.id === session.id
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-slate-700'
              }`}
            >
              <div className="text-sm font-medium">{session.name}</div>
              
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 flex-1 overflow-y-auto">
        <h3 className="text-sm uppercase tracking-wider text-slate-400 font-semibold mb-2">Players on Ice</h3>
        {selectedSession ? (
          <div className="flex flex-col gap-1">
            {players.map(player => (
              <button
                key={player.id}
                onClick={() => onSelectPlayer(player)}
                className={`text-left px-3 py-2 rounded flex items-center justify-between transition-colors ${
                  selectedPlayer?.id === player.id
                    ? 'bg-blue-600 text-white'
                    : 'hover:bg-slate-700'
                }`}
              >
                <span className="font-medium text-sm">{player.name}</span>
                <span className="text-xs opacity-75">#{player.id}</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500 italic">Select a session first</p>
        )}
      </div>

      <MiniMap 
        videoRef={videoRef}
        trackingData={trackingData}
        fps={fps}
        selectedPlayerId={selectedPlayer?.id}
      />
    </div>
  );
};
