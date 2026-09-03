import express from 'express';
import path from 'path';
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

// Serve static assets from project root
app.use(express.static(__dirname, {
  extensions: ['html', 'htm'],
  index: 'index.html'
}));

// Route fallback: if route matches a subfolder with index.html or root index.html
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
