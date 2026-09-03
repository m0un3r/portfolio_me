import express from 'express';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// In-memory store for contact form submissions
const submissions = [];

// Form submission API
app.post('/api/submit-form', (req, res) => {
  const submission = {
    ...req.body,
    receivedAt: new Date().toISOString()
  };
  submissions.push(submission);
  console.log('[Form Submission]', JSON.stringify(submission, null, 2));
  res.json({
    success: true,
    message: 'Message received successfully',
    id: submissions.length
  });
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', uptime: process.uptime() });
});

// Offline location API endpoint (replaces external api.fetch.tools)
app.get('/api/location', (req, res) => {
  res.json({
    country: 'Italy',
    city: 'Milan',
    country_code: 'IT',
    latitude: 45.4642,
    longitude: 9.1900
  });
});

// Redirect nested case study links if misresolved
app.use((req, res, next) => {
  const match = req.path.match(/^\/case-study\/[^/]+\/([a-z0-9-]+)$/i);
  if (match) {
    const target = `/case-study/${match[1]}`;
    if (fs.existsSync(path.join(__dirname, 'case-study', match[1], 'index.html'))) {
      return res.redirect(301, target);
    }
  }
  next();
});

// Redirect trailing slash to non-trailing slash for cleaner canonical paths
app.use((req, res, next) => {
  if (req.path.length > 1 && req.path.endsWith('/')) {
    const query = req.url.slice(req.path.length);
    return res.redirect(301, req.path.slice(0, -1) + query);
  }
  next();
});

// Middleware to handle Framer CMS range queries: ?range=from-to[,from2-to2...]
app.use((req, res, next) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    return next();
  }

  const rangeQuery = req.query.range;
  if (!rangeQuery) {
    return next();
  }

  // Resolve file path safely
  const relativePath = req.path.replace(/^\/+/, '');
  const filePath = path.resolve(__dirname, relativePath);
  if (!filePath.startsWith(__dirname) || !fs.existsSync(filePath)) {
    return next();
  }

  try {
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) {
      return next();
    }

    const rangeStr = Array.isArray(rangeQuery) ? rangeQuery.join(',') : String(rangeQuery);
    const parts = rangeStr.split(',').map(s => s.trim()).filter(Boolean);
    if (parts.length === 0) {
      return next();
    }

    const ranges = [];
    let totalLength = 0;
    for (const part of parts) {
      const match = part.match(/^(\d+)-(\d+)$/);
      if (!match) {
        return res.status(400).send('Invalid range format');
      }
      const start = parseInt(match[1], 10);
      const end = parseInt(match[2], 10);
      if (start > end || start < 0) {
        return res.status(400).send('Invalid range bounds');
      }
      const length = end - start + 1;
      ranges.push({ start, end, length });
      totalLength += length;
    }

    const buffer = Buffer.alloc(totalLength);
    const fd = fs.openSync(filePath, 'r');
    let offset = 0;
    for (const r of ranges) {
      fs.readSync(fd, buffer, offset, r.length, r.start);
      offset += r.length;
    }
    fs.closeSync(fd);

    res.status(200);
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Length', totalLength);
    res.setHeader('Accept-Ranges', 'bytes');
    res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
    return res.end(buffer);
  } catch (err) {
    console.error('[Range Query Error]', err);
    return res.status(500).send('Internal server error');
  }
});

// Middleware to resolve subfolder index.html without requiring trailing slash
app.use((req, res, next) => {
  // If requesting a path with a file extension, skip directory check
  if (path.extname(req.path)) {
    return next();
  }

  const cleanPath = req.path.replace(/^\/+|\/+$/g, '');
  if (cleanPath) {
    const candidateIndex = path.join(__dirname, cleanPath, 'index.html');
    if (fs.existsSync(candidateIndex)) {
      return res.sendFile(candidateIndex);
    }
  }
  next();
});

// Serve static assets from project root
app.use(express.static(__dirname, {
  extensions: ['html', 'htm'],
  index: 'index.html'
}));

// Route fallback: if route matches a subfolder with index.html or root index.html
app.get('*', (req, res) => {
  if (path.extname(req.path)) {
    return res.status(404).send('Not Found');
  }
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
