export interface Player {
  id: string;
  name: string;
  number: number;
}

export const mockPlayers: Player[] = [
  { id: '1', name: 'Connor McDavid', number: 97 },
  { id: '2', name: 'Auston Matthews', number: 34 },
  { id: '3', name: 'Nathan MacKinnon', number: 29 },
  { id: '4', name: 'Cale Makar', number: 8 },
];

export interface Session {
  id: string;
  date: string;
  time: string;
}

export const mockSessions: Session[] = [
  { id: '1', date: '2023-11-01', time: '18:00 - 19:30' },
  { id: '2', date: '2023-11-02', time: '10:00 - 11:30' },
];
