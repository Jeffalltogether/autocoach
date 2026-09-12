import { describe, it, expect } from 'vitest';
import { extractDriveId, getDirectVideoUrl, getProxyJsonUrl } from './urlParser';

describe('urlParser', () => {
  const validUrl = 'https://drive.google.com/file/d/1Ds9SSdqss6Q_W4fSXl8xwxwI-ehycibE/view?usp=drive_link';
  const validId = '1Ds9SSdqss6Q_W4fSXl8xwxwI-ehycibE';
  
  describe('extractDriveId', () => {
    it('should extract the ID from a valid Google Drive URL', () => {
      expect(extractDriveId(validUrl)).toBe(validId);
    });

    it('should return null for invalid URLs', () => {
      expect(extractDriveId('https://google.com')).toBeNull();
      expect(extractDriveId('invalid_string')).toBeNull();
    });

    it('should return null for empty strings or undefined', () => {
      expect(extractDriveId('')).toBeNull();
      expect(extractDriveId(undefined)).toBeNull();
    });
  });

  describe('getDirectVideoUrl', () => {
    it('should convert a Drive URL to a uc download URL', () => {
      expect(getDirectVideoUrl(validUrl)).toBe(`https://drive.google.com/uc?export=download&id=${validId}`);
    });

    it('should return the original string if it is not a Drive URL', () => {
      const fallbackUrl = 'https://example.com/video.mp4';
      expect(getDirectVideoUrl(fallbackUrl)).toBe(fallbackUrl);
    });
  });

  describe('getProxyJsonUrl', () => {
    it('should convert a Drive URL to an API proxy URL', () => {
      expect(getProxyJsonUrl(validUrl)).toBe(`/api/drive?id=${validId}`);
    });

    it('should return the original string if it is not a Drive URL', () => {
      const fallbackUrl = '/local/data.json';
      expect(getProxyJsonUrl(fallbackUrl)).toBe(fallbackUrl);
    });
  });
});
