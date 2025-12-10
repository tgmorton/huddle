import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { GameScreen } from './components/GameScreen'
import { SandboxScreen } from './components/Sandbox/SandboxScreen'
import { PocketScreen } from './components/Pocket/PocketScreen'
import { RoutesScreen } from './components/Routes/RoutesScreen'
import { TeamRoutesScreen } from './components/TeamRoutes/TeamRoutesScreen'
import { PlaySimScreen } from './components/PlaySim/PlaySimScreen'
import { IntegratedSimScreen } from './components/IntegratedSim'
import { ManagementScreenWrapper } from './components/Management'
import { AdminScreen } from './components/Admin'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <nav className="app-nav">
        <Link to="/">Game</Link>
        <Link to="/sandbox">Sandbox</Link>
        <Link to="/pocket">Pocket</Link>
        <Link to="/routes">Routes</Link>
        <Link to="/team-routes">Team</Link>
        <Link to="/play-sim">Play</Link>
        <Link to="/integrated">Integrated</Link>
        <Link to="/manage">Manage</Link>
        <Link to="/admin">Admin</Link>
      </nav>
      <Routes>
        <Route path="/" element={<GameScreen />} />
        <Route path="/sandbox" element={<SandboxScreen />} />
        <Route path="/pocket" element={<PocketScreen />} />
        <Route path="/routes" element={<RoutesScreen />} />
        <Route path="/team-routes" element={<TeamRoutesScreen />} />
        <Route path="/play-sim" element={<PlaySimScreen />} />
        <Route path="/integrated" element={<IntegratedSimScreen />} />
        <Route path="/manage" element={<ManagementScreenWrapper />} />
        <Route path="/admin" element={<AdminScreen />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
