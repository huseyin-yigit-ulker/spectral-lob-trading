import { useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, Target, ShieldAlert, Zap } from 'lucide-react';
import { createChart } from 'lightweight-charts';

export default function Dashboard() {
  const [stats, setStats] = useState({ trades: 0, screener: 0 });
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    async function fetchStats() {
      const { count: tradeCount } = await supabase.from('trade_logs').select('*', { count: 'exact', head: true });
      const { count: screenerCount } = await supabase.from('screener_history').select('*', { count: 'exact', head: true });
      setStats({ trades: tradeCount || 0, screener: screenerCount || 0 });
    }
    fetchStats();
  }, []);

  // Lightweight Charts Initialization
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: { timeVisible: true, secondsVisible: false }
    });

    const series = chart.addAreaSeries({
      lineColor: '#3b82f6', topColor: 'rgba(59, 130, 246, 0.4)', bottomColor: 'rgba(59, 130, 246, 0.0)', lineWidth: 2
    });

    // Mock initial flatline data just for aesthetics until real PnL is tracked
    series.setData([
      { time: '2026-10-01', value: 0 },
      { time: '2026-10-02', value: 0 },
      { time: '2026-10-03', value: 0 }
    ]);
    
    chartRef.current = chart;

    const handleResize = () => { chart.applyOptions({ width: chartContainerRef.current.clientWidth }); };
    window.addEventListener('resize', handleResize);
    
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#1f2937] pb-4">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">System Overview</h2>
          <p className="text-sm text-gray-500 mt-1">Live metrics and strategy performance.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs font-bold text-green-400">SYSTEM ONLINE</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard icon={<Target size={20} />} label="Total Signals" value={stats.trades} color="blue" />
        <StatCard icon={<Activity size={20} />} label="Coins Scanned" value={stats.screener} color="green" />
        <StatCard icon={<Zap size={20} />} label="Win Rate" value="--%" color="yellow" />
        <StatCard icon={<ShieldAlert size={20} />} label="Active Strategy" value="V5 SMC" color="purple" />
      </div>

      <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl p-6 shadow-xl">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Cumulative PnL (Mock/Flat)</h3>
        <div ref={chartContainerRef} className="w-full h-[300px]" />
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  const colorMap = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  };
  return (
    <div className="bg-[#0b0e14] p-5 rounded-xl border border-[#1f2937] flex items-center gap-4 hover:border-gray-600 transition-colors">
      <div className={`p-3 rounded-lg border ${colorMap[color]}`}>{icon}</div>
      <div>
        <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-black text-gray-100">{value}</p>
      </div>
    </div>
  );
}
