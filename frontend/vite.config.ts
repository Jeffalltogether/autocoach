import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite';
import type { ViteDevServer } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'
import fs from 'fs'
import path from 'path'

function sessionsApiPlugin() {
  return {
    name: 'sessions-api',
    configureServer(server: ViteDevServer) {
      server.middlewares.use('/api/sessions', (_req: IncomingMessage, res: ServerResponse) => {
        const processedDir = path.resolve(__dirname, '../data/processed');
        const rawDir = path.resolve(__dirname, '../data/raw');
        
        let processedFiles: string[] = [];
        try { processedFiles = fs.readdirSync(processedDir); } catch (e) {}
        
        let rawFiles: string[] = [];
        try { rawFiles = fs.readdirSync(rawDir); } catch (e) {}

        const jsonFiles = processedFiles.filter(f => f.endsWith('.json'));
        
        const sessions = jsonFiles.map((jsonFile, idx) => {
          const baseName = jsonFile.replace('_tracking.json', '').replace('.json', '');
          
          let videoUrl = '';
          
          // 1. Try to find a matching raw video
          const rawMatch = rawFiles.find(f => 
            f.endsWith('.mp4') && 
            (f.includes(baseName) || baseName.includes(f.replace('.mp4','')) || 
            (baseName === 'hockey_test' && f === 'hocky_test_video.mp4'))
          );
          
          if (rawMatch) {
            videoUrl = `/raw/${rawMatch}`;
          } else {
            // 2. Fallback to a processed video
            const processedMatch = processedFiles.find(f => f.endsWith('.mp4') && f.includes(baseName));
            if (processedMatch) {
              videoUrl = `/processed/${processedMatch}`;
            }
          }

          let name = baseName.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
          if (name.toLowerCase() === 'hockey test') name = 'Hockey Test (Short)';
          
          return {
            id: (idx + 1).toString(),
            name,
            videoUrl,
            jsonUrl: `/processed/${jsonFile}`
          };
        });

        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(sessions));
      });
    }
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), sessionsApiPlugin()],
})
