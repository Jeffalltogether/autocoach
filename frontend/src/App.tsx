import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Toolbar } from './components/Toolbar';
import { VideoPlayer } from './components/VideoPlayer';
import { TimelinePlot } from './components/TimelinePlot';
import { MiniMap } from './components/MiniMap';
import { TrackletStitcher } from './components/TrackletStitcher';
import { getDirectVideoUrl, getProxyJsonUrl } from './utils/urlParser';
import { fetchAssignments, saveAssignments } from './api';
import type { RosterPlayer } from './api';

export interface Session { id: string; name: string; videoUrl: string; jsonUrl: string; }

export interface Keypoint { x: number; y: number; conf: number; }
export interface Entity {
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  conf?: number;
  real_x?: number;
  real_y?: number;
}
export interface PlayerTracking {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  real_x?: number;
  real_y?: number;
  has_puck?: boolean;
  in_contact?: boolean;
  velocity_mph?: number;
  keypoints?: Keypoint[];
  stick_vector?: { dx: number; dy: number };
}
export interface FrameData { frame: number; players: PlayerTracking[]; entities?: Entity[]; }

export interface Player { id: number; name: string; firstFrame: number; lastFrame: number; }

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [trackingData, setTrackingData] = useState<FrameData[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [roster, setRoster] = useState<RosterPlayer[]>([]);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [ignoredTracks, setIgnoredTracks] = useState<number[]>([]);
  const [showStitcher, setShowStitcher] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [playerStats, setPlayerStats] = useState<Record<string, any>>({});
  const [showAllBoundingBoxes, setShowAllBoundingBoxes] = useState(true);
  const [showPlayerBoundingBox, setShowPlayerBoundingBox] = useState(false);
  const [showAllPoses, setShowAllPoses] = useState(true);
  const [showPlayerPose, setShowPlayerPose] = useState(false);
  const [trackPlayer, setTrackPlayer] = useState(false);
  const [loopPlayer, setLoopPlayer] = useState(false);
  const [showPucks, setShowPucks] = useState(false);
  const [puckConfThreshold, setPuckConfThreshold] = useState(0.3);
  const [cropSize, setCropSize] = useState(400);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [fps] = useState(30);

  // Fetch sessions from the static configuration file
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const res = await fetch('/sessions.json');
        const data: any[] = await res.json();
          const mappedData: Session[] = data.map(s => {
            const videoUrl = s.driveVideoUrl ? getDirectVideoUrl(s.driveVideoUrl) : (s.videoUrl || '');
            const jsonUrl = s.driveJsonUrl ? getProxyJsonUrl(s.driveJsonUrl) : (s.jsonUrl || '');
            return { ...s, videoUrl, jsonUrl };
          });
          
          setSessions(mappedData);
          if (mappedData.length > 0) setSelectedSession(mappedData[0]);
      } catch (err) {
        console.error("Error loading sessions", err);
      }
    };
    loadSessions();
  }, []);

  // Fetch tracking data when session changes
  useEffect(() => {
    if (!selectedSession) return;
    
    // Clear out old state immediately while loading
    setTrackingData([]);
    setPlayers([]);
    setSelectedPlayer(null);

    fetch(selectedSession.jsonUrl)
      .then(res => res.json())
      .then((data) => {
        // Handle both old flat array format and new nested object format
        const framesArray: FrameData[] = Array.isArray(data) ? data : (data.frames || []);
        const stats = Array.isArray(data) ? {} : (data.player_stats || {});
        
        setTrackingData(framesArray);
        setPlayerStats(stats);
        
        // Extract unique players and their first/last appearance
        const playerMap = new Map<number, {first: number, last: number}>();
        framesArray.forEach(frame => {
          frame.players.forEach(p => {
            if (!playerMap.has(p.id)) {
              playerMap.set(p.id, {first: frame.frame, last: frame.frame});
            } else {
              playerMap.get(p.id)!.last = frame.frame;
            }
          });
        });
        
        const extractedPlayers = Array.from(playerMap.entries()).map(([id, frames]) => ({
          id,
          name: `Player #${id}`,
          firstFrame: frames.first,
          lastFrame: frames.last
        })).sort((a, b) => a.id - b.id);
        
        setPlayers(extractedPlayers);
        if (extractedPlayers.length > 0) {
          setSelectedPlayer(extractedPlayers[0]);
        }

        // Fetch roster assignments from local API
        const handleRosterData = (rosterData: any) => {
          let loadedRoster = rosterData?.roster || [];
          let loadedAssignments = rosterData?.assignments || {};
          let loadedIgnored = rosterData?.ignored_tracks || [];
          
          if (loadedRoster.length === 0) {
            const defaultColors = ['#ef4444', '#3b82f6', '#22c55e', '#eab308', '#a855f7', '#f97316', '#06b6d4', '#ec4899'];
            loadedRoster = extractedPlayers.map((p, idx) => ({
              id: `r_${p.id}`,
              name: p.name,
              jersey: '',
              color: defaultColors[idx % defaultColors.length]
            }));
            extractedPlayers.forEach(p => {
              loadedAssignments[p.id.toString()] = `r_${p.id}`;
            });
          }
          
          setRoster(loadedRoster);
          setAssignments(loadedAssignments);
          setIgnoredTracks(loadedIgnored);
        };

        // Fetch roster assignments from local API
        fetchAssignments(selectedSession.id)
          .then(handleRosterData)
          .catch(err => {
            console.warn("Could not load roster assignments from API. Using local auto-populated state.", err);
            handleRosterData({});
          });

      })
      .catch(err => console.error("Error loading pose tracking data", err));
  }, [selectedSession]);

  const handleSelectPlayer = (p: Player) => {
    setSelectedPlayer(p);
    // Jump video to first appearance
    if (videoRef.current) {
      videoRef.current.currentTime = p.firstFrame / fps;
      videoRef.current.play().catch(() => {});
    }
  };

  return (
    <div className="flex flex-col md:flex-row h-screen w-screen bg-slate-900 overflow-hidden font-sans text-slate-200">
      <Sidebar 
        sessions={sessions}
        players={players}
        selectedSession={selectedSession}
        selectedPlayer={selectedPlayer}
        playerStats={playerStats}
        onSelectSession={setSelectedSession}
        onSelectPlayer={handleSelectPlayer}
        onOpenStitcher={() => setShowStitcher(true)}
      />

      {showStitcher && selectedSession && (
        <TrackletStitcher
          roster={roster}
          assignments={assignments}
          ignoredTracks={ignoredTracks}
          players={players}
          trackingData={trackingData}
          onClose={() => setShowStitcher(false)}
          onSelectPlayer={handleSelectPlayer}
          onUpdate={(newRoster, newAssignments, newIgnored) => {
            setRoster(newRoster);
            setAssignments(newAssignments);
            setIgnoredTracks(newIgnored);
            saveAssignments(selectedSession.id, {
              version: "1.0",
              video_id: selectedSession.id,
              roster: newRoster,
              assignments: newAssignments,
              ignored_tracks: newIgnored
            }).catch(e => console.error("Failed to save assignments to API", e));
          }}
        />
      )}
      
      <div className="flex-1 flex flex-col min-w-0">
        <VideoPlayer 
          videoRef={videoRef}
          videoUrl={selectedSession?.videoUrl || ''}
          trackingData={trackingData}
          roster={roster}
          assignments={assignments}
          ignoredTracks={ignoredTracks}
          selectedPlayerId={selectedPlayer?.id}
          selectedPlayerFirstFrame={selectedPlayer?.firstFrame}
          selectedPlayerLastFrame={selectedPlayer?.lastFrame}
          showAllBoundingBoxes={showAllBoundingBoxes}
          showPlayerBoundingBox={showPlayerBoundingBox}
          showAllPoses={showAllPoses}
          showPlayerPose={showPlayerPose}
          trackPlayer={trackPlayer}
          loopPlayer={loopPlayer}
          showPucks={showPucks}
          puckConfThreshold={puckConfThreshold}
          cropSize={cropSize}
          fps={fps}
        />
        
        <div className="h-[45vh] min-h-[200px] shrink-0 flex flex-col border-t border-slate-700 custom-scrollbar bg-slate-900">
          <TimelinePlot 
            videoRef={videoRef}
            trackingData={trackingData} 
            selectedPlayerId={selectedPlayer?.id}
            fps={fps}
            onSeek={(time) => {
              if (videoRef.current) videoRef.current.currentTime = time;
            }}
          />
          
          <MiniMap 
            videoRef={videoRef}
            trackingData={trackingData}
            roster={roster}
            assignments={assignments}
            ignoredTracks={ignoredTracks}
            fps={fps}
            selectedPlayerId={selectedPlayer?.id}
          />
        </div>
        
        <Toolbar 
          videoRef={videoRef}
          videoKey={selectedSession?.videoUrl}
          onSeekToStart={() => {
            if (videoRef.current && selectedPlayer) {
              videoRef.current.currentTime = selectedPlayer.firstFrame / fps;
            }
          }}
          onSeekToEnd={() => {
            if (videoRef.current && selectedPlayer) {
              videoRef.current.currentTime = selectedPlayer.lastFrame / fps;
            }
          }}
          showAllBoundingBoxes={showAllBoundingBoxes}
          setShowAllBoundingBoxes={setShowAllBoundingBoxes}
          showPlayerBoundingBox={showPlayerBoundingBox}
          setShowPlayerBoundingBox={setShowPlayerBoundingBox}
          showAllPoses={showAllPoses}
          setShowAllPoses={setShowAllPoses}
          showPlayerPose={showPlayerPose}
          setShowPlayerPose={setShowPlayerPose}
          trackPlayer={trackPlayer}
          setTrackPlayer={setTrackPlayer}
          loopPlayer={loopPlayer}
          setLoopPlayer={setLoopPlayer}
          showPucks={showPucks}
          setShowPucks={setShowPucks}
          puckConfThreshold={puckConfThreshold}
          setPuckConfThreshold={setPuckConfThreshold}
          cropSize={cropSize}
          setCropSize={setCropSize}
        />
      </div>
    </div>
  );
}

export default App;
