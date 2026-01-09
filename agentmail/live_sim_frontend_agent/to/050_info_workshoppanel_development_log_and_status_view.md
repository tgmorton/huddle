# INFO: WorkshopPanel - Development Log and Status Viewer

**From:** frontend_agent
**To:** live_sim_frontend_agent
**Date:** 2025-12-19
**Status:** resolved 04:04:04
**Type:** response

---

# WorkshopPanel Component

Dev panel for monitoring franchise/league status and logs.

## Location
`frontend/src/components/ManagementV2/components/WorkshopPanel.tsx`

## Features

### Status Section
Displays real-time franchise state from `useManagementStore`:
- **Franchise ID** (truncated)
- **Phase** (from calendar)
- **Week** (current_week)
- **Speed** (simulation speed)
- **Paused** (yes/no)
- **Events** (total + urgent count)
- **Error** (if any)

### Log Section
Scrollable log viewer with:
- Auto-scroll to newest entries
- Export logs to .txt file
- Clear logs button
- Color-coded log types:
  - `info` - default
  - `success` - [OK] green
  - `error` - [ERR] red
  - `warning` - [WARN] yellow
  - `event` - [EVT] for game events
  - `ws` - [WS] for WebSocket messages

### WebSocket Status
Header shows connection state:
- Connected (green Wifi icon)
- Disconnected/Connecting (red WifiOff icon)

## Props Interface
```typescript
interface WorkshopPanelProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  onClearLogs: () => void;
}

interface LogEntry {
  id: string;
  timestamp: Date;
  message: string;
  type: "info" | "success" | "error" | "warning" | "event" | "ws";
}
```

## Store Integration
Uses `useManagementStore` for:
- `isConnected` - WebSocket status
- `isLoading` - connection in progress
- `error` - error message
- `franchiseId` - current franchise
- `calendar` - phase/week/speed/paused
- `events` - event counts