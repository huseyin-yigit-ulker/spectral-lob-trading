import fs from 'fs';
import path from 'path';

const distDir = path.resolve('dist');
const indexHtml = path.join(distDir, 'index.html');

if (fs.existsSync(indexHtml)) {
  const content = fs.readFileSync(indexHtml, 'utf8');

  // 1. Create 404.html so Render / GitHub Pages / Static servers fallback to SPA
  fs.writeFileSync(path.join(distDir, '404.html'), content);

  // 2. Create physical directories and index.html copies for each SPA route
  const routes = ['signals', 'public', 'screener', 'live', 'trades'];
  routes.forEach(route => {
    const routeDir = path.join(distDir, route);
    if (!fs.existsSync(routeDir)) {
      fs.mkdirSync(routeDir, { recursive: true });
    }
    fs.writeFileSync(path.join(routeDir, 'index.html'), content);
  });

  console.log('[Postbuild] SPA routes (signals, public, screener, live, trades) & 404.html generated successfully.');
} else {
  console.warn('[Postbuild] dist/index.html not found, skipping route generation.');
}
