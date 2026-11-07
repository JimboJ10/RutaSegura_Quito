// Vite aislado para la auditoría. No modifica .env ni los servidores habituales.
import { createServer } from 'vite';
process.env.VITE_API_BASE_URL = '/api';
const server = await createServer({
  server: { host: '127.0.0.1', port: 5185, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8802', rewrite: url => url.replace(/^\/api/, '') } },
  },
});
await server.listen();
server.printUrls();
