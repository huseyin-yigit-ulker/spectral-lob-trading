import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, Target, ShieldAlert } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({ trades: 0, screener: 0 });

  useEffect(() => {
    async function fetchStats() {
      const { count: tradeCount } = await supabase
        .from('trade_logs')
        .select('*', { count: 'exact', head: true });
        
      const { count: screenerCount } = await supabase
        .from('screener_history')
        .select('*', { count: 'exact', head: true });

      setStats({
        trades: tradeCount || 0,
        screener: screenerCount || 0
      });
    }
    fetchStats();
  }, []);

  return (
    <div className="space-y-6 mt-4">
      <h2 className="text-2xl font-bold border-b border-gray-700 pb-2">Sistem Özeti</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 flex items-center gap-4 shadow-lg">
          <div className="bg-blue-900/50 p-3 rounded-full">
            <Target className="text-blue-400 w-8 h-8" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Toplam İşlem Sinyali</p>
            <p className="text-3xl font-bold">{stats.trades}</p>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 flex items-center gap-4 shadow-lg">
          <div className="bg-green-900/50 p-3 rounded-full">
            <Activity className="text-green-400 w-8 h-8" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Taranan Coin Sayısı (Screener)</p>
            <p className="text-3xl font-bold">{stats.screener}</p>
          </div>
        </div>

        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 flex items-center gap-4 shadow-lg">
          <div className="bg-purple-900/50 p-3 rounded-full">
            <ShieldAlert className="text-purple-400 w-8 h-8" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Aktif Model</p>
            <p className="text-xl font-bold text-purple-400">V5 Dynamic SMC</p>
          </div>
        </div>
      </div>
    </div>
  );
}
