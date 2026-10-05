import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Screener from './pages/Screener';
import TradeLogs from './pages/TradeLogs';
import LiveTerminal from './pages/LiveTerminal';
import { Activity, LayoutDashboard, List, Terminal, Globe, TerminalSquare } from 'lucide-react';
import { useState, useEffect } from 'react';

function Topbar() {
  const [utcTime, setUtcTime] = useState('');

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="h-14 border-b border-[#1f2937] bg-[#0B0E11] flex items-center justify-between px-6 shrink-0 sticky top-0 z-40">
      <div className="flex items-center gap-2">
        <Terminal className="text-[#F0B90B]" size={20} />
        <span className="font-black text-white tracking-tight">QUANT<span className="text-[#F0B90B]">V5</span></span>
      </div>
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-2 text-gray-400 text-xs font-mono bg-[#1E2329] px-3 py-1 rounded-md border border-[#2B3139]">
          <Globe size={12} className="text-[#F0B90B]" />
          {utcTime || '00:00:00 UTC'}
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-[10px] font-black text-green-400 tracking-wider">SYSTEM ONLINE</span>
        </div>
      </div>
    </div>
  );
}

function Sidebar() {
  const loc = useLocation();
  const links = [
    { to: '/', icon: <LayoutDashboard size={18} />, label: 'Dashboard' },
    { to: '/screener', icon: <Activity size={18} />, label: 'Market Scanner' },
    { to: '/live', icon: <TerminalSquare size={18} />, label: 'Live Terminal' },
    { to: '/trades', icon: <List size={18} />, label: 'Signal Logs' },
  ];

  return (
    <div className="w-64 bg-[#0B0E11] border-r border-[#1f2937] flex flex-col hidden md:flex shrink-0">
      <div className="p-4 space-y-2 flex-1">
        {links.map((l) => {
          const isActive = loc.pathname === l.to;
          return (
            <Link 
              key={l.to} 
              to={l.to}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-bold transition-all ${
                isActive 
                  ? 'bg-[#1E2329] text-[#F0B90B] border border-[#2B3139]' 
                  : 'text-gray-400 hover:text-white hover:bg-[#121822]'
              }`}
            >
              {l.icon}
              {l.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function MobileNav() {
  const loc = useLocation();
  const links = [
    { to: '/', icon: <LayoutDashboard size={20} /> },
    { to: '/screener', icon: <Activity size={20} /> },
    { to: '/live', icon: <TerminalSquare size={20} /> },
    { to: '/trades', icon: <List size={20} /> },
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-[#0B0E11] border-t border-[#1f2937] flex items-center justify-around z-50">
      {links.map((l) => (
        <Link 
          key={l.to} 
          to={l.to}
          className={`p-3 rounded-full ${
            loc.pathname === l.to ? 'text-[#F0B90B] bg-[#1E2329]' : 'text-gray-500'
          }`}
        >
          {l.icon}
        </Link>
      ))}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen bg-[#0B0E11] text-[#EAECEF] overflow-hidden selection:bg-[#F0B90B]/30">
        <Topbar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-[#0B0E11] p-4 md:p-8 pb-24 md:pb-8">
            <div className="max-w-7xl mx-auto">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/screener" element={<Screener />} />
                <Route path="/live" element={<LiveTerminal />} />
                <Route path="/trades" element={<TradeLogs />} />
              </Routes>
            </div>
          </main>
        </div>
        <MobileNav />
      </div>
    </BrowserRouter>
  );
}

