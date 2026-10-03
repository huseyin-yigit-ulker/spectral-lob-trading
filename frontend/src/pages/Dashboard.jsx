import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, Target, ShieldAlert, Zap } from 'lucide-react';
import EquityCurvePanel from '../components/EquityCurvePanel';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';

export default function Dashboard() {
  const [stats, setStats] = useState({ trades: 0, screener: 0 });
  const [recentTrades, setRecentTrades] = useState([]);
  const [activeTrade, setActiveTrade] = useState(null);

  useEffect(() => {
    async function fetchData() {
      const { count: tradeCount } = await supabase.from('trade_logs').select('*', { count: 'exact', head: true });
      const { count: screenerCount } = await supabase.from('screener_history').select('*', { count: 'exact', head: true });
      setStats({ trades: tradeCount || 0, screener: screenerCount || 0 });

      const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: false }).limit(4);
      if (data) setRecentTrades(data);
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Target size={20} />} label="Total Signals" value={stats.trades} color="blue" />
        <StatCard icon={<Activity size={20} />} label="Coins Scanned" value={stats.screener} color="green" />
        <StatCard icon={<Zap size={20} />} label="Win Rate" value="--%" color="yellow" />
        <StatCard icon={<ShieldAlert size={20} />} label="Active Strategy" value="V5 SMC" color="purple" />
      </div>

      <EquityCurvePanel data={recentTrades} />

      <div>
        <h3 className="text-xl font-black text-gray-100 mb-4 tracking-tight">Recent Signals</h3>
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
    green: 'bg-green-500/10 text-green-400 border-green-500/20',
    yellow: 'bg-yellow-500/10 text-[#F0B90B] border-[#F0B90B]/20', // Binance Yellow
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
