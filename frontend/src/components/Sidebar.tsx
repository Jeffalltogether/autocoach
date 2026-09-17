import type { Session } from '../App';
import type { Player } from '../App';
import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface SidebarProps {
  sessions: Session[];
  players: Player[];
  selectedSession: Session | null;
  selectedPlayer: Player | null;
  playerStats: Record<string, any>;
  onSelectSession: (s: Session) => void;
  onSelectPlayer: (p: Player) => void;
  onOpenStitcher?: () => void;
}

const CustomTick = ({ payload, x, y, textAnchor, stroke, radius }: any) => {
  const parts = payload.value.includes('-') ? payload.value.split('-') : [payload.value];
  return (
    <g className="recharts-layer recharts-polar-angle-axis-tick">
      <text radius={radius} stroke={stroke} x={x} y={y} className="recharts-text recharts-polar-angle-axis-tick-value" textAnchor={textAnchor} fill="#94a3b8" fontSize={11}>
        {parts.map((part: string, index: number) => {
          const content = index < parts.length - 1 ? `${part}-` : part;
          const dy = parts.length > 1 ? (index === 0 ? -4 : 12) : 0;
          return <tspan x={x} dy={dy} key={index}>{content}</tspan>;
        })}
      </text>
    </g>
  );
};

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  players,
  selectedSession,
  selectedPlayer,
  playerStats,
  onSelectSession,
  onSelectPlayer,
  onOpenStitcher
}) => {
  return (
    <div className="w-full md:w-64 md:h-full h-48 md:max-h-none bg-slate-800 text-slate-100 flex flex-col md:flex-col overflow-hidden border-b md:border-r border-slate-700 shrink-0">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-blue-400">AutoCoach</h2>
        {onOpenStitcher && (
          <button 
            onClick={onOpenStitcher}
            className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-2 py-1 rounded shadow"
          >
            Stitch Tracks
          </button>
        )}
      </div>
      <div className="p-4 border-b border-slate-700">
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

      {selectedPlayer && playerStats && playerStats[selectedPlayer.id] && (
        <div className="p-4 border-t border-slate-700 bg-slate-900 flex-shrink-0">
          <h3 className="text-sm uppercase tracking-wider text-slate-400 font-semibold mb-2">Player Card</h3>
          <div className="bg-slate-800 rounded-lg p-3 shadow-inner">
            <div className="text-center font-bold text-lg text-blue-400 mb-2">{selectedPlayer.name}</div>
            
            {/* Radar Chart */}
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart 
                  cx="50%" cy="50%" outerRadius="65%" 
                  data={[
                    { subject: 'Hustle', A: playerStats[selectedPlayer.id].radar_scores?.hustle ?? Math.min(100, (playerStats[selectedPlayer.id].total_distance_ft || 0) * 1.5), fullMark: 100 },
                    { subject: 'Speed', A: playerStats[selectedPlayer.id].radar_scores?.speed ?? Math.min(100, (playerStats[selectedPlayer.id].max_velocity_mph || 0) * 4), fullMark: 100 },
                    { subject: 'Energizer', A: playerStats[selectedPlayer.id].radar_scores?.energizer ?? Math.min(100, (playerStats[selectedPlayer.id].possession_time_sec || 0) * 30), fullMark: 100 },
                    { subject: 'Globe-Trotter', A: playerStats[selectedPlayer.id].radar_scores?.globe_trotter ?? Math.min(100, (playerStats[selectedPlayer.id].globe_trotter_pct || 0) * 3.33), fullMark: 100 }
                  ]}
                >
                  <PolarGrid stroke="#475569" />
                  <PolarAngleAxis dataKey="subject" tick={<CustomTick />} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Player" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.5} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Raw Values */}
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="bg-slate-700 rounded p-2 text-center">
                <div className="text-xs text-slate-400">Distance</div>
                <div className="font-bold text-sm">{playerStats[selectedPlayer.id].total_distance_ft?.toFixed(1) || 0} ft</div>
              </div>
              <div className="bg-slate-700 rounded p-2 text-center">
                <div className="text-xs text-slate-400">Speed Bursts</div>
                <div className="font-bold text-sm">{playerStats[selectedPlayer.id].speed_bursts ?? Math.floor((playerStats[selectedPlayer.id].max_velocity_mph || 0) / 4)}</div>
              </div>
              <div className="bg-slate-700 rounded p-2 text-center">
                <div className="text-xs text-slate-400">Energizer Ratio</div>
                <div className="font-bold text-sm">{((playerStats[selectedPlayer.id].energizer_ratio ?? Math.min(1, (playerStats[selectedPlayer.id].possession_time_sec || 0) / 2)) * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-slate-700 rounded p-2 text-center">
                <div className="text-xs text-slate-400">Globe-Trotter</div>
                <div className="font-bold text-sm">{(playerStats[selectedPlayer.id].globe_trotter_pct || 0).toFixed(1)}%</div>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
