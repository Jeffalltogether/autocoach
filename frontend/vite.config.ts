import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import type { ViteDevServer } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'
import fs from 'fs'
import path from 'path'

function sessionsApiPlugin() {
  return {
    name: 'sessions-api',
    configureServer(server: ViteDevServer) {
      server.middlewares.use('/api/sessions', (_req: IncomingMessage, res: ServerResponse) => {
        const processedDir = path.resolve(import.meta.dirname, '../data/processed');
        const rawDir = path.resolve(import.meta.dirname, '../data/raw');
        
        let processedFiles: string[] = [];
        try { processedFiles = fs.readdirSync(processedDir); } catch (_e) { /* empty */ }
        
        let rawFiles: string[] = [];
        try { rawFiles = fs.readdirSync(rawDir); } catch (_e) { /* empty */ }

        // Find all tracking JSONs
        const jsonFiles = processedFiles.filter(f => f.endsWith('_tracking.json') || f.endsWith('.json'));

        const sessions = jsonFiles.map((jsonFile, idx) => {
          // Strip _tracking.json to get the base name (e.g. "hocky_test_video", "pro_game")
          const baseName = jsonFile.replace('_tracking.json', '').replace('.json', '');
          
          let videoUrl = '';
          
          // 1. Try exact match in raw (baseName + .mp4)
          if (rawFiles.includes(baseName + '.mp4')) {
            videoUrl = `/raw/${baseName}.mp4`;
          } else {
            // 2. Try fuzzy: find a raw file whose name (without .mp4) is a substring of baseName or vice versa
            const rawMatch = rawFiles.find(f => {
              if (!f.endsWith('.mp4')) return false;
              const rawBase = f.replace('.mp4', '');
              return baseName.includes(rawBase) || rawBase.includes(baseName);
            });
            if (rawMatch) {
              videoUrl = `/raw/${rawMatch}`;
            } else {
              // 3. Fallback to processed output video
              const processedMatch = processedFiles.find(f => f.endsWith('.mp4') && f.includes(baseName));
              if (processedMatch) {
                videoUrl = `/processed/${processedMatch}`;
              }
            }
          }

          // Build display name from base
          const displayName = baseName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (l: string) => l.toUpperCase());
          
          return {
            id: (idx + 1).toString(),
            name: displayName,
            videoUrl,
            jsonUrl: `/processed/${jsonFile}`
          };
        });

        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(sessions));
      });
    }
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), sessionsApiPlugin()],
})
