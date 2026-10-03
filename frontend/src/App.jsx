import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity, LayoutDashboard, Radar } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import TradeLogs from './pages/TradeLogs';
import Screener from './pages/Screener';

function Navbar() {
  const location = useLocation();
  const navItems = [
    { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { path: '/trades', label: 'Trade Logs', icon: <Activity size={18} /> },
    { path: '/screener', label: 'Screener', icon: <Radar size={18} /> }
  ];

  return (
    <nav className="bg-[#0b0e14] border-b border-[#1f2937] sticky top-0 z-50">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-black text-sm tracking-tighter">V5</span>
          </div>
          <h1 className="text-xl font-bold text-gray-100 tracking-tight">Quant Engine</h1>
        </div>
        <div className="flex gap-2">
          {navItems.map(item => {
            const isActive = location.pathname === item.path;
            return (
              <Link 
                key={item.path} 
                to={item.path} 
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${isActive ? 'bg-blue-500/10 text-blue-400' : 'text-gray-400 hover:bg-[#1f2937] hover:text-gray-200'}`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#06080c] text-gray-200 font-sans selection:bg-blue-500/30">
        <Navbar />
        <main className="container mx-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/trades" element={<TradeLogs />} />
            <Route path="/screener" element={<Screener />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
