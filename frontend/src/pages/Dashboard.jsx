import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { calculateTransactions } from '../utils/transactions';
import { Activity, Target, ShieldAlert, Zap, Clock, ArrowRight, TrendingUp, TrendingDown } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({ transactions: 0, screener: 0, winRate: 0, pnl: 0 });
  const [transactions, setTransactions] = useState([]);
  const [liveMetrics, setLiveMetrics] = useState([]);
  const [screenerHistory, setScreenerHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      // 1. Fetch Trade Logs for Transactions
      const { data: logsData } = await supabase
        .from('trade_logs')
        .select('*')
        .order('zaman', { ascending: true });
        
      if (logsData) {
        const txs = calculateTransactions(logsData);
        setTransactions(txs);
        
        const wins = txs.filter(t => t.win).length;
        const total = txs.length;
        const wr = total > 0 ? ((wins / total) * 100).toFixed(1) : 0;
        const totalPnl = txs.reduce((acc, val) => acc + val.pnl_pct, 0).toFixed(2);
        
        setStats(prev => ({ ...prev, transactions: total, winRate: wr, pnl: totalPnl }));
      }

      // 2. Fetch Live Metrics (Tracked Symbols)
      const { data: metricsData } = await supabase
        .from('live_metrics')
        .select('*')
        .order('updated_at', { ascending: false });
      
      if (metricsData) {
        setLiveMetrics(metricsData);
      }

      // 3. Fetch Screener History
      const { data: screenerData } = await supabase
        .from('screener_history')
        .select('*')
        .order('zaman', { ascending: false })
        .limit(30); // Get last 30 scans
      
      if (screenerData) {
        setScreenerHistory(screenerData);
        setStats(prev => ({ ...prev, screener: screenerData.length })); // Just an indicator
      }

      setLoading(false);
    }
    
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-[#1f2937] pb-4">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">System & Transactions</h2>
          <p className="text-sm text-gray-500 mt-1">Unified view of screener, active symbols, and closed transactions.</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs font-bold text-green-400">SYSTEM ONLINE</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard icon={<Target size={20} />} label="Total Transactions" value={stats.transactions} color="blue" />
        <StatCard icon={<Zap size={20} />} label="Win Rate" value={`${stats.winRate}%`} color="yellow" />
        <StatCard icon={<Activity size={20} />} label="Cumulative PnL" value={`${stats.pnl > 0 ? '+' : ''}${stats.pnl}%`} color={stats.pnl >= 0 ? "green" : "red"} />
        <StatCard icon={<ShieldAlert size={20} />} label="Active Strategy" value="V5 SMC" color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Tracked Symbols / Live Metrics */}
        <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl flex flex-col h-[600px]">
          <div className="p-4 border-b border-[#1f2937] bg-[#121822] rounded-t-xl">
            <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
              <Activity size={16} className="text-blue-400"/> Takipteki Semboller (Live)
            </h3>
          </div>
          <div className="p-4 flex-1 overflow-y-auto space-y-3">
            {loading ? <p className="text-gray-500 text-sm">Loading...</p> : 
             liveMetrics.length === 0 ? <p className="text-gray-500 text-sm">Takip edilen sembol yok.</p> :
             liveMetrics.map((m, i) => (
              <div key={i} className="flex justify-between items-center p-3 bg-[#1E2329] rounded-lg border border-[#2B3139]">
                <div>
                  <div className="font-bold text-white">{m.sembol}</div>
                  <div className="text-xs text-gray-400 mt-1">{new Date(m.updated_at).toLocaleTimeString()}</div>
                </div>
                <div className="text-right">
                  <div className={`text-xs font-bold px-2 py-1 rounded ${m.smc_status?.includes('BULLISH') ? 'bg-green-500/20 text-green-400' : m.smc_status?.includes('BEARISH') ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}`}>
                    {m.smc_status || 'NEUTRAL'}
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1">FVG Depth: {Number(m.fvg_depth).toFixed(2)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Transactions */}
        <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl flex flex-col h-[600px]">
          <div className="p-4 border-b border-[#1f2937] bg-[#121822] rounded-t-xl">
            <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
              <Target size={16} className="text-green-400"/> Tamamlanan İşlemler
            </h3>
          </div>
          <div className="p-4 flex-1 overflow-y-auto space-y-3">
            {loading ? <p className="text-gray-500 text-sm">Loading...</p> : 
             transactions.length === 0 ? <p className="text-gray-500 text-sm">İşlem bulunamadı.</p> :
             transactions.map((t, i) => (
              <div key={i} className="p-3 bg-[#1E2329] rounded-lg border border-[#2B3139]">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-white">{t.sembol}</span>
                  <span className={`text-xs font-bold px-2 py-1 rounded flex items-center gap-1 ${t.tip === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {t.tip === 'LONG' ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                    {t.tip}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-gray-400 mb-2">
                  <div>Giriş: {Number(t.entry_price).toFixed(4)}</div>
                  <ArrowRight size={12} className="text-gray-600"/>
                  <div>Çıkış: {Number(t.exit_price).toFixed(4)}</div>
                </div>
                <div className="flex justify-between items-end">
                  <div className="text-[10px] text-gray-500 flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(t.exit_time).toLocaleTimeString()}
                  </div>
                  <div className={`font-mono font-bold ${t.win ? 'text-green-400' : 'text-red-400'}`}>
                    {t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Screener History */}
        <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl flex flex-col h-[600px]">
          <div className="p-4 border-b border-[#1f2937] bg-[#121822] rounded-t-xl">
            <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
              <Clock size={16} className="text-yellow-400"/> Screener Geçmişi (Son Tarama)
            </h3>
          </div>
          <div className="p-4 flex-1 overflow-y-auto space-y-3">
            {loading ? <p className="text-gray-500 text-sm">Loading...</p> : 
             screenerHistory.length === 0 ? <p className="text-gray-500 text-sm">Tarama geçmişi yok.</p> :
             screenerHistory.map((s, i) => (
              <div key={i} className={`flex justify-between items-center p-3 rounded-lg border ${s.durum === 'KABUL' ? 'bg-[#1E2329] border-[#F0B90B]/30' : 'bg-[#121822] border-[#2B3139]'}`}>
                <div>
                  <div className="font-bold text-white flex items-center gap-2">
                    {s.sembol} 
                    {s.durum === 'KABUL' && <span className="text-[10px] bg-[#F0B90B] text-black px-1.5 py-0.5 rounded font-bold">KABUL</span>}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{new Date(s.zaman).toLocaleTimeString()}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-300">Skor: {Number(s.skor).toFixed(1)}</div>
                  <div className="text-[10px] text-gray-500 mt-1">FVG Mesafe: %{Number(s.fvg_mesafe_yuzde).toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  const colorMap = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20'
  };
  return (
    <div className="bg-[#0b0e14] p-5 rounded-xl border border-[#1f2937] flex items-center gap-4 hover:border-gray-600 transition-colors">
      <div className={`p-3 rounded-lg border ${colorMap[color]}`}>{icon}</div>
      <div>
        <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">{label}</p>
        <p className={`text-2xl font-black ${color === 'red' ? 'text-red-400' : color === 'green' ? 'text-green-400' : 'text-gray-100'}`}>{value}</p>
      </div>
    </div>
  );
}
