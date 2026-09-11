import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Toolbar } from './components/Toolbar';
import { VideoPlayer } from './components/VideoPlayer';
import { TimelinePlot } from './components/TimelinePlot';
import { mockSessions } from './mockData';
import type { Session } from './mockData';

export interface Keypoint { x: number; y: number; conf: number; }
export interface PlayerTracking { id: number; x: number; y: number; width: number; height: number; keypoints?: Keypoint[]; }
export interface FrameData { frame: number; players: PlayerTracking[]; }

export interface Player { id: number; name: string; firstFrame: number; }

function App() {
  const [selectedSession, setSelectedSession] = useState<Session | null>(mockSessions[0]);
  const [trackingData, setTrackingData] = useState<FrameData[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true);
  const [showPose, setShowPose] = useState(true);
  const [trackPlayer, setTrackPlayer] = useState(false);
  const [cropSize, setCropSize] = useState(400);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const [fps] = useState(30);

  // Fetch tracking data
  useEffect(() => {
    fetch('/pose_tracking.json')
      .then(res => res.json())
      .then((data: FrameData[]) => {
        setTrackingData(data);
        
        // Extract unique players and their first appearance
        const playerMap = new Map<number, number>();
        data.forEach(frame => {
          frame.players.forEach(p => {
            if (!playerMap.has(p.id)) {
              playerMap.set(p.id, frame.frame);
            }
          });
        });
        
        const extractedPlayers = Array.from(playerMap.entries()).map(([id, firstFrame]) => ({
          id,
          name: `Player #${id}`,
          firstFrame
        })).sort((a, b) => a.id - b.id);
        
        setPlayers(extractedPlayers);
        if (extractedPlayers.length > 0) {
          setSelectedPlayer(extractedPlayers[0]);
        }
      })
      .catch(err => console.error("Error loading pose tracking data", err));
  }, []);

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
        sessions={mockSessions}
        players={players}
        selectedSession={selectedSession}
        selectedPlayer={selectedPlayer}
        onSelectSession={setSelectedSession}
        onSelectPlayer={(p) => handleSelectPlayer(p)}
      />
      
      <div className="flex-1 flex flex-col min-w-0">
        <VideoPlayer 
          videoRef={videoRef}
          trackingData={trackingData}
          selectedPlayerId={selectedPlayer?.id}
          showBoundingBoxes={showBoundingBoxes}
          showPose={showPose}
          trackPlayer={trackPlayer}
          cropSize={cropSize}
          fps={fps}
        />
        
        <TimelinePlot 
          trackingData={trackingData} 
          selectedPlayerId={selectedPlayer?.id}
          fps={fps}
          onSeek={(time) => {
            if (videoRef.current) videoRef.current.currentTime = time;
          }}
        />
        
        <Toolbar 
          showBoundingBoxes={showBoundingBoxes}
          setShowBoundingBoxes={setShowBoundingBoxes}
          showPose={showPose}
          setShowPose={setShowPose}
          trackPlayer={trackPlayer}
          setTrackPlayer={setTrackPlayer}
          cropSize={cropSize}
          setCropSize={setCropSize}
        />
      </div>
    </div>
  );
}

export default App;
