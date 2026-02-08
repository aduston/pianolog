# Pianolog Frontend (React Pilot)

This app is an incremental migration target for the existing Flask + Socket.IO UI.

## Commands

```bash
npm install
npm run dev
npm run build
npm run preview
```

## Runtime notes

- `npm run dev` starts Vite on port `5173` and proxies `/api` + `/socket.io` to Flask (`http://localhost:5000`).
- `npm run build` outputs production assets to `../static/react`.
- Flask serves the built React app at `/react`.
