import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { calculateTransactions } from '../utils/transactions';
import { Activity, Target, ShieldAlert, Zap, Clock, ArrowRight, TrendingUp, TrendingDown, Layers } from 'lucide-react';
import PnlChart from '../components/Chart';

export default function Dashboard() {
  const [stats, setStats] = useState({ transactions: 0, active: 0, winRate: 0, pnl: 0, profitFactor: 0 });
  const [closedTransactions, setClosedTransactions] = useState([]);
  const [activeTransactions, setActiveTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      const { data: logsData } = await supabase
        .from('trade_logs')
        .select('*')
        .order('zaman', { ascending: true });
        
      if (logsData) {
        const txs = calculateTransactions(logsData);
        setClosedTransactions(txs.closed);
        setActiveTransactions(txs.active);
        
        const wins = txs.closed.filter(t => t.win);
        const losses = txs.closed.filter(t => !t.win);
        
        const wr = txs.closed.length > 0 ? ((wins.length / txs.closed.length) * 100).toFixed(1) : 0;
        const totalPnl = txs.closed.reduce((acc, val) => acc + val.pnl_pct, 0).toFixed(2);
        
        const grossProfit = wins.reduce((acc, val) => acc + val.pnl_pct, 0);
        const grossLoss = Math.abs(losses.reduce((acc, val) => acc + val.pnl_pct, 0));
        const profitFactor = grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : (grossProfit > 0 ? '∞' : 0);
        
        setStats(prev => ({ 
          ...prev, 
          transactions: txs.closed.length, 
          active: txs.active.length,
          winRate: wr, 
          pnl: totalPnl,
          profitFactor
        }));
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
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">SMC Terminal <span className="text-[#F0B90B]">V5</span></h2>
          <p className="text-sm text-gray-500 mt-1">High-Frequency Trading & Smart Money Concepts</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          <span className="text-xs font-bold text-green-400">SNIPER MODE ACTIVE</span>
        </div>
      </div>
      
      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <StatCard icon={<Activity size={20} />} label="Net PnL" value={`${stats.pnl > 0 ? '+' : ''}${stats.pnl}%`} color={stats.pnl >= 0 ? "green" : "red"} />
        <StatCard icon={<Zap size={20} />} label="Win Rate" value={`${stats.winRate}%`} color="yellow" />
        <StatCard icon={<TrendingUp size={20} />} label="Profit Factor" value={stats.profitFactor} color="blue" />
        <StatCard icon={<Target size={20} />} label="Closed Trades" value={stats.transactions} color="purple" />
        <StatCard icon={<Layers size={20} />} label="Active Positions" value={stats.active} color="yellow" pulse={stats.active > 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Chart Column (Takes up 2 cols on large screens) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl overflow-hidden">
            <div className="p-4 border-b border-[#1f2937] bg-[#121822]">
              <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
                <TrendingUp size={16} className="text-[#F0B90B]"/> Cumulative Equity Curve
              </h3>
            </div>
            <div className="p-4">
               {loading ? <div className="h-[300px] flex items-center justify-center text-gray-500">Loading Chart...</div> : 
                <PnlChart data={closedTransactions} />
               }
            </div>
          </div>

          <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl overflow-hidden">
             <div className="p-4 border-b border-[#1f2937] bg-[#121822] flex justify-between items-center">
              <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
                <Target size={16} className="text-green-400"/> Active Positions
              </h3>
              {stats.active > 0 && <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>}
            </div>
            <div className="p-4 space-y-3">
               {loading ? <p className="text-gray-500 text-sm">Loading...</p> : 
                activeTransactions.length === 0 ? <p className="text-gray-500 text-sm">No active positions currently.</p> :
                activeTransactions.map((t, i) => (
                  <div key={i} className="flex justify-between items-center p-4 bg-green-500/5 rounded-lg border border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.1)]">
                    <div>
                      <div className="font-bold text-white flex items-center gap-2 text-lg">
                        {t.sembol}
                        <span className={`text-xs font-bold px-2 py-1 rounded flex items-center gap-1 ${t.tip === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {t.tip === 'LONG' ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                          {t.tip}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 mt-1">Entry: {Number(t.entry_price).toFixed(4)}</div>
                    </div>
                    <div className="text-right">
                       <div className="text-sm text-gray-400">Position Open</div>
                       <div className="text-xs text-green-400 mt-1 animate-pulse">Waiting for SMC Exit...</div>
                    </div>
                  </div>
                ))
               }
            </div>
          </div>
        </div>

        {/* Closed Transactions Column */}
        <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl flex flex-col h-[700px]">
          <div className="p-4 border-b border-[#1f2937] bg-[#121822] rounded-t-xl">
            <h3 className="text-sm font-bold text-gray-300 uppercase flex items-center gap-2">
              <Clock size={16} className="text-gray-400"/> Recent History
            </h3>
          </div>
          <div className="p-4 flex-1 overflow-y-auto space-y-3">
            {loading ? <p className="text-gray-500 text-sm">Loading...</p> : 
             closedTransactions.length === 0 ? <p className="text-gray-500 text-sm">No closed trades yet.</p> :
             closedTransactions.slice(0, 15).map((t, i) => (
              <div key={i} className={`p-3 rounded-lg border ${t.win ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-white text-sm">{t.sembol}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-1 ${t.tip === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {t.tip}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-gray-400 mb-2">
                  <div>{Number(t.entry_price).toFixed(4)}</div>
                  <ArrowRight size={12} className="text-gray-600 mx-1"/>
                  <div>{Number(t.exit_price).toFixed(4)}</div>
                </div>
                <div className="flex justify-between items-end">
                  <div className="text-[10px] text-gray-500">
                    {new Date(t.exit_time).toLocaleTimeString()}
                  </div>
                  <div className={`font-mono font-bold text-sm ${t.win ? 'text-green-400' : 'text-red-400'}`}>
                    {t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color, pulse }) {
  const colorMap = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-green-400 border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.1)]',
    yellow: 'bg-[#F0B90B]/10 text-[#F0B90B] border-[#F0B90B]/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    red: 'bg-red-500/10 text-red-400 border-red-500/20'
  };
  return (
    <div className={`bg-[#0b0e14] p-5 rounded-xl border border-[#1f2937] flex items-center gap-4 hover:border-gray-600 transition-colors ${pulse ? 'animate-pulse' : ''}`}>
      <div className={`p-3 rounded-lg border ${colorMap[color]}`}>{icon}</div>
      <div>
        <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">{label}</p>
        <p className={`text-2xl font-black ${color === 'red' ? 'text-red-400' : color === 'green' ? 'text-green-400' : color === 'yellow' ? 'text-[#F0B90B]' : 'text-gray-100'}`}>{value}</p>
      </div>
    </div>
  );
}
