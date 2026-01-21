import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { GameScreen } from './components/GameScreen'
import { SandboxScreen } from './components/Sandbox/SandboxScreen'
import { PocketScreen } from './components/Pocket/PocketScreen'
import { RoutesScreen } from './components/Routes/RoutesScreen'
import { TeamRoutesScreen } from './components/TeamRoutes/TeamRoutesScreen'
import { PlaySimScreen } from './components/PlaySim/PlaySimScreen'
import { IntegratedSimScreen } from './components/IntegratedSim'
import { ManagementScreenWrapper } from './components/Management'
import { AdminScreen } from './components/Admin'
import { V2SimScreen } from './components/V2Sim/V2SimScreen'
import { AgentMailScreen } from './components/AgentMail/AgentMailScreen'
import { PlayerCardDemo } from './components/PlayerCard'
import { ManagementV2 } from './components/ManagementV2'
import { GameView } from './components/GameView'
import { SimAnalyzer } from './components/SimAnalyzer/SimAnalyzer'
import { Sim3D } from './components/Sim3D'
import { ArmsPrototype } from './components/ArmsPrototype'
import SimExplorer from './components/SimExplorer/SimExplorer'
import { BroadcastLab } from './components/BroadcastLab'
import './App.css'

// Theme management at app level
function useTheme() {
  const [sepiaMode, setSepiaMode] = useState(() => {
    return localStorage.getItem('sepia-mode') === 'true'
  });

  useEffect(() => {
    if (sepiaMode) {
      document.documentElement.classList.add('sepia-mode')
    } else {
      document.documentElement.classList.remove('sepia-mode')
    }
  }, [sepiaMode]);

  const toggleTheme = () => {
    const newValue = !sepiaMode
    setSepiaMode(newValue)
    localStorage.setItem('sepia-mode', String(newValue))
  }

  return { sepiaMode, toggleTheme };
}

// Navigation header for non-AgentMail views
const NAV_ITEMS = [
  { path: '/', label: 'Game' },
  { path: '/coach', label: 'Coach' },
  { path: '/sandbox', label: 'Sandbox' },
  { path: '/pocket', label: 'Pocket' },
  { path: '/routes', label: 'Routes' },
  { path: '/team-routes', label: 'Team Routes' },
  { path: '/play-sim', label: 'Play Sim' },
  { path: '/integrated', label: 'Integrated' },
  { path: '/v2-sim', label: 'V2 Sim' },
  { path: '/sim-analyzer', label: 'Sim Analyzer' },
  { path: '/sim-3d', label: 'Sim 3D' },
  { path: '/arms', label: 'Arms Proto' },
  { path: '/manage', label: 'Manage' },
  { path: '/manage-v2', label: 'Manage V2' },
  { path: '/sim-explorer', label: 'Sim Explorer' },
  { path: '/admin', label: 'Admin' },
  { path: '/agentmail', label: 'AgentMail' },
  { path: '/player-card', label: 'Player Card' },
  { path: '/broadcast-lab', label: 'Broadcast Lab' },
];

function AppHeader() {
  const location = useLocation();

  return (
    <header className="app-header">
      <nav className="app-nav">
        {NAV_ITEMS.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`app-nav-link ${location.pathname === item.path ? 'active' : ''}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}

function WithHeader({ children }: { children: ReactNode }) {
  return (
    <div className="app-with-header">
      <AppHeader />
      <div className="app-content">
        {children}
      </div>
    </div>
  );
}

function App() {
  // Initialize theme
  useTheme();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<WithHeader><GameScreen /></WithHeader>} />
        <Route path="/sandbox" element={<WithHeader><SandboxScreen /></WithHeader>} />
        <Route path="/pocket" element={<WithHeader><PocketScreen /></WithHeader>} />
        <Route path="/routes" element={<WithHeader><RoutesScreen /></WithHeader>} />
        <Route path="/team-routes" element={<WithHeader><TeamRoutesScreen /></WithHeader>} />
        <Route path="/play-sim" element={<WithHeader><PlaySimScreen /></WithHeader>} />
        <Route path="/integrated" element={<WithHeader><IntegratedSimScreen /></WithHeader>} />
        <Route path="/v2-sim" element={<WithHeader><V2SimScreen /></WithHeader>} />
        {/* SimAnalyzer - V2 sim with ManagementV2 design (standalone, no header) */}
        <Route path="/sim-analyzer" element={<SimAnalyzer />} />
        {/* Sim3D - Three.js 3D simulation viewer (standalone, no header) */}
        <Route path="/sim-3d" element={<Sim3D />} />
        {/* Arms Prototype - 1v1 OL/DL physics simulation (standalone, no header) */}
        <Route path="/arms" element={<ArmsPrototype />} />
        <Route path="/manage" element={<WithHeader><ManagementScreenWrapper /></WithHeader>} />
        {/* ManagementV2 - Redesign prototype (standalone, no header) */}
        <Route path="/manage-v2" element={<ManagementV2 />} />
        {/* GameView - Coach's game day experience (standalone, no header) */}
        <Route path="/coach" element={<GameView />} />
        {/* SimExplorer - Historical simulation explorer (standalone, no header) */}
        <Route path="/sim-explorer" element={<SimExplorer />} />
        <Route path="/admin" element={<WithHeader><AdminScreen /></WithHeader>} />
        {/* AgentMail has its own sidebar navigation, no header needed */}
        <Route path="/agentmail" element={<AgentMailScreen />} />
        {/* Player Card prototype - standalone demo */}
        <Route path="/player-card" element={<PlayerCardDemo />} />
        {/* Broadcast Lab - TV graphics prototypes (standalone, no header) */}
        <Route path="/broadcast-lab" element={<BroadcastLab />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
