import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('sessions.json configuration', () => {
  it('should be valid JSON and have required fields', () => {
    // Read the file directly to validate structure
    const sessionsPath = path.resolve(__dirname, '../public/sessions.json');
    const rawData = fs.readFileSync(sessionsPath, 'utf-8');
    const sessions = JSON.parse(rawData);

    expect(Array.isArray(sessions)).toBe(true);

    sessions.forEach((session: any, index: number) => {
      expect(session).toHaveProperty('id');
      expect(session.id).toBeTypeOf('string');
      
      expect(session).toHaveProperty('name');
      expect(session.name).toBeTypeOf('string');

      // It must have either a local videoUrl OR a driveVideoUrl
      const hasLocalVideo = typeof session.videoUrl === 'string' && session.videoUrl.length > 0;
      const hasDriveVideo = typeof session.driveVideoUrl === 'string' && session.driveVideoUrl.length > 0;
      expect(hasLocalVideo || hasDriveVideo).toBe(true);

      // It must have either a local jsonUrl OR a driveJsonUrl
      const hasLocalJson = typeof session.jsonUrl === 'string' && session.jsonUrl.length > 0;
      const hasDriveJson = typeof session.driveJsonUrl === 'string' && session.driveJsonUrl.length > 0;
      expect(hasLocalJson || hasDriveJson).toBe(true);

      if (hasDriveVideo) {
        expect(session.driveVideoUrl).toMatch(/^https:\/\/drive\.google\.com\//);
      }
      
      if (hasDriveJson) {
        expect(session.driveJsonUrl).toMatch(/^https:\/\/drive\.google\.com\//);
      }
    });
  });
});
