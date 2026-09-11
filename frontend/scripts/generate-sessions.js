import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const processedDir = path.resolve(__dirname, '../public/processed');
const rawDir = path.resolve(__dirname, '../public/raw');
const outputJson = path.resolve(__dirname, '../public/sessions.json');

let processedFiles = [];
try { processedFiles = fs.readdirSync(processedDir); } catch (e) {}

let rawFiles = [];
try { rawFiles = fs.readdirSync(rawDir); } catch (e) {}

const jsonFiles = processedFiles.filter(f => f.endsWith('.json'));

const sessions = jsonFiles.map((jsonFile, idx) => {
    const baseName = jsonFile.replace('_tracking.json', '').replace('.json', '').replace('_processed', '');
    
    let videoUrl = '';
    
    // 1. Try to find a matching raw video
    const rawMatch = rawFiles.find(f => 
    f.endsWith('.mp4') && 
    (f.includes(baseName) || baseName.includes(f.replace('.mp4','')))
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

    let name = baseName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    return {
    id: (idx + 1).toString(),
    name,
    videoUrl,
    jsonUrl: `/processed/${jsonFile}`
    };
});

fs.writeFileSync(outputJson, JSON.stringify(sessions, null, 2));
console.log(`Generated sessions.json with ${sessions.length} sessions.`);
