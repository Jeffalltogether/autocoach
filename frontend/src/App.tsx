import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Toolbar } from './components/Toolbar';
import { VideoPlayer } from './components/VideoPlayer';
import { TimelinePlot } from './components/TimelinePlot';

export interface Session { id: string; name: string; videoUrl: string; jsonUrl: string; }

export interface Keypoint { x: number; y: number; conf: number; }
export interface PlayerTracking { id: number; x: number; y: number; width: number; height: number; keypoints?: Keypoint[]; }
export interface FrameData { frame: number; players: PlayerTracking[]; }

export interface Player { id: number; name: string; firstFrame: number; lastFrame: number; }

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [trackingData, setTrackingData] = useState<FrameData[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  
  const [showAllBoundingBoxes, setShowAllBoundingBoxes] = useState(false);
  const [showPlayerBoundingBox, setShowPlayerBoundingBox] = useState(true);
  const [showAllPoses, setShowAllPoses] = useState(false);
  const [showPlayerPose, setShowPlayerPose] = useState(true);
  const [trackPlayer, setTrackPlayer] = useState(false);
  const [loopPlayer, setLoopPlayer] = useState(false);
  const [cropSize, setCropSize] = useState(400);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [fps] = useState(30);

  // Fetch dynamic sessions
  useEffect(() => {
    fetch('/api/sessions')
      .then(res => res.json())
      .then((data: Session[]) => {
        setSessions(data);
        if (data.length > 0) {
          setSelectedSession(data[0]);
        }
      })
      .catch(err => console.error("Error loading sessions API", err));
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
      .then((data: FrameData[]) => {
        setTrackingData(data);
        
        // Extract unique players and their first/last appearance
        const playerMap = new Map<number, {first: number, last: number}>();
        data.forEach(frame => {
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
    <div className="flex h-screen w-screen bg-slate-900 overflow-hidden font-sans text-slate-200">
      <Sidebar 
        sessions={sessions}
        players={players}
        selectedSession={selectedSession}
        selectedPlayer={selectedPlayer}
        onSelectSession={setSelectedSession}
        onSelectPlayer={(p) => handleSelectPlayer(p)}
      />
      
      <div className="flex-1 flex flex-col min-w-0">
        <VideoPlayer 
          videoRef={videoRef}
          videoUrl={selectedSession?.videoUrl || ''}
          trackingData={trackingData}
          selectedPlayerId={selectedPlayer?.id}
          selectedPlayerFirstFrame={selectedPlayer?.firstFrame}
          selectedPlayerLastFrame={selectedPlayer?.lastFrame}
          showAllBoundingBoxes={showAllBoundingBoxes}
          showPlayerBoundingBox={showPlayerBoundingBox}
          showAllPoses={showAllPoses}
          showPlayerPose={showPlayerPose}
          trackPlayer={trackPlayer}
          loopPlayer={loopPlayer}
          cropSize={cropSize}
          fps={fps}
        />
        
        <TimelinePlot 
          videoRef={videoRef}
          trackingData={trackingData} 
          selectedPlayerId={selectedPlayer?.id}
          fps={fps}
          onSeek={(time) => {
            if (videoRef.current) videoRef.current.currentTime = time;
          }}
        />
        
        <Toolbar 
          videoRef={videoRef}
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
          cropSize={cropSize}
          setCropSize={setCropSize}
        />
      </div>
    </div>
  );
}

export default App;
