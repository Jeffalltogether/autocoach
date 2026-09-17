export interface RosterPlayer {
  id: string;
  name: string;
  jersey: string;
  color: string;
}

export interface RosterAssignments {
  version: string;
  video_id: string;
  roster: RosterPlayer[];
  assignments: Record<string, string>;
  ignored_tracks: number[];
}

const API_BASE = 'http://localhost:8000/api';

export const fetchAssignments = async (videoId: string): Promise<RosterAssignments> => {
  const res = await fetch(`${API_BASE}/assignments/${videoId}`);
  if (!res.ok) throw new Error('Failed to fetch assignments');
  return res.json();
};

export const saveAssignments = async (videoId: string, payload: RosterAssignments): Promise<void> => {
  const res = await fetch(`${API_BASE}/assignments/${videoId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to save assignments');
};
