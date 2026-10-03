import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, Target, ShieldAlert, Zap } from 'lucide-react';
import EquityCurvePanel from '../components/EquityCurvePanel';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';
import { reconstructTrades } from '../utils/tradeLogic';

export default function Dashboard() {
  const [stats, setStats] = useState({ trades: 0, screener: 0 });
  const [recentTrades, setRecentTrades] = useState([]);
  const [closedTrades, setClosedTrades] = useState([]);
  const [activeTrade, setActiveTrade] = useState(null);
  const [tradeStats, setTradeStats] = useState({ totalPnl: 0, winRate: 0, totalClosed: 0 });

  useEffect(() => {
    async function fetchData() {
      const { count: screenerCount } = await supabase.from('screener_history').select('*', { count: 'exact', head: true });
      
      const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: true });
      if (data) {
        const parsed = reconstructTrades(data);
        setTradeStats(parsed.stats);
        setRecentTrades(parsed.allTrades.slice(0, 4));
        setClosedTrades(parsed.closedTrades);
        setStats({ trades: parsed.allTrades.length, screener: screenerCount || 0 });
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Target size={20} />} label="Total Positions" value={stats.trades} color="blue" />
        <StatCard icon={<Activity size={20} />} label="Coins Scanned" value={stats.screener} color="green" />
        <StatCard icon={<Zap size={20} />} label="Win Rate" value={`${tradeStats.winRate.toFixed(1)}%`} color="yellow" />
        <StatCard icon={<ShieldAlert size={20} />} label="Total PnL" value={`${tradeStats.totalPnl > 0 ? '+' : ''}${tradeStats.totalPnl.toFixed(2)}%`} color={tradeStats.totalPnl >= 0 ? 'green' : 'red'} />
      </div>

      <EquityCurvePanel data={closedTrades} />

      <div>
        <h3 className="text-xl font-black text-gray-100 mb-4 tracking-tight">Recent Positions</h3>
        {recentTrades.length === 0 ? (
          <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl p-8 text-center text-gray-500">
            Awaiting new signals...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {recentTrades.map(trade => (
              <SignalCard key={trade.id} trade={trade} onClick={setActiveTrade} />
            ))}
          </div>
        )}
      </div>

      {activeTrade && (
        <ChartModal trade={activeTrade} onClose={() => setActiveTrade(null)} />
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }) {
  const colorMap = {
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    green: 'bg-green-500/10 text-[#0ECB81] border-[#0ECB81]/20',
    red: 'bg-red-500/10 text-[#F6465D] border-[#F6465D]/20',
    yellow: 'bg-yellow-500/10 text-[#F0B90B] border-[#F0B90B]/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  };
  return (
    <div className="bg-[#0B0E11] p-5 rounded-xl border border-[#1f2937] flex items-center gap-4 hover:border-gray-600 transition-colors">
      <div className={`p-3 rounded-lg border ${colorMap[color]}`}>{icon}</div>
      <div>
        <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-black text-gray-100 font-mono">{value}</p>
      </div>
    </div>
  );
}
