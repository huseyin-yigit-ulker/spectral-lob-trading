import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';
import { reconstructTrades, parseUtcDate } from '../utils/tradeLogic';
import { Filter, List, Activity, TrendingUp, TrendingDown, Target, Zap } from 'lucide-react';

const PERIODS = [
  { id: 'all', label: 'Tüm Zamanlar' },
  { id: '24h', label: 'Son 24 Saat' },
  { id: '7d', label: 'Son 7 Gün' },
  { id: '30d', label: 'Son 30 Gün' },
];

export default function TradeLogs() {
  const [allReconstructedTrades, setAllReconstructedTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTrade, setActiveTrade] = useState(null);
  const [period, setPeriod] = useState('all');

  const fetchLogs = async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: true });
    if (data) {
      const parsed = reconstructTrades(data);
      setAllReconstructedTrades(parsed.allTrades);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000);
    return () => clearInterval(interval);
  }, []);

  const filteredTrades = useMemo(() => {
    if (period === 'all') return allReconstructedTrades;
    
    const now = new Date().getTime();
    let limitMs = 0;
    
    if (period === '24h') limitMs = 24 * 60 * 60 * 1000;
    else if (period === '7d') limitMs = 7 * 24 * 60 * 60 * 1000;
    else if (period === '30d') limitMs = 30 * 24 * 60 * 60 * 1000;

    return allReconstructedTrades.filter(t => {
      const tradeTime = parseUtcDate(t.giris_zaman).getTime();
      return (now - tradeTime) <= limitMs;
    });
  }, [allReconstructedTrades, period]);

  // Periyot bazli metrikler
  const periodStats = useMemo(() => {
    const closed = filteredTrades.filter(t => t.status === 'CLOSED');
    const active = filteredTrades.filter(t => t.status === 'OPEN');
    const wins = closed.filter(t => t.pnl_yuzde > 0);
    const losses = closed.filter(t => t.pnl_yuzde <= 0);
    const totalPnl = closed.reduce((acc, t) => acc + (t.pnl_yuzde || 0), 0);
    const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;

    return {
      total: filteredTrades.length,
      closedCount: closed.length,
      activeCount: active.length,
      wins: wins.length,
      losses: losses.length,
      winRate: winRate.toFixed(1),
      totalPnl: totalPnl.toFixed(2),
    };
  }, [filteredTrades]);

  return (
    <div className="space-y-6 relative h-full flex flex-col">
      {/* Top Header Bar */}
      <div className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 border-b border-[#1f2937] pb-6 shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-2xl font-black text-gray-100 tracking-tight flex items-center gap-2">
              <List className="text-[#F0B90B]" size={24} /> Signal Terminal
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
              UTC LIVE
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">Live V5 SMC Execution Logs, Entry/Exit Prices & PnL History</p>
        </div>
        
        {/* Segmented Period Filter */}
        <div className="flex items-center gap-3 bg-[#121822] p-1.5 rounded-xl border border-[#1f2937] shadow-sm overflow-x-auto w-full xl:w-auto">
          <div className="flex bg-[#0B0E11] p-1 rounded-lg border border-[#1f2937] w-full shrink-0">
            {PERIODS.map(p => (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-5 py-2 rounded-md text-xs font-bold transition-all whitespace-nowrap flex-1 text-center ${
                  period === p.id 
                    ? 'bg-[#2B3139] text-[#F0B90B] shadow-md' 
                    : 'text-gray-500 hover:text-gray-300 hover:bg-[#1E2329]'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Period Quick Stats Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Filtrelenen İşlemler</span>
            <span className="text-lg font-black text-gray-100 font-mono">{periodStats.total}</span>
            <span className="text-[10px] text-gray-500 ml-1.5 font-mono">({periodStats.closedCount} kapalı)</span>
          </div>
          <Zap size={20} className="text-[#F0B90B]/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Açık Pozisyonlar</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-lg font-black text-amber-400 font-mono">{periodStats.activeCount}</span>
              {periodStats.activeCount > 0 && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              )}
            </div>
          </div>
          <Activity size={20} className="text-amber-400/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Kazanma Oranı</span>
            <span className="text-lg font-black text-emerald-400 font-mono">%{periodStats.winRate}</span>
            <span className="text-[10px] text-gray-500 ml-1.5 font-mono">({periodStats.wins}W / {periodStats.losses}L)</span>
          </div>
          <Target size={20} className="text-emerald-400/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Net PnL</span>
            <span className={`text-lg font-black font-mono ${Number(periodStats.totalPnl) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {Number(periodStats.totalPnl) >= 0 ? '+' : ''}{periodStats.totalPnl}%
            </span>
          </div>
          {Number(periodStats.totalPnl) >= 0 ? (
            <TrendingUp size={20} className="text-emerald-400/60" />
          ) : (
            <TrendingDown size={20} className="text-rose-400/60" />
          )}
        </div>
      </div>
      
      {/* Grid of Cards */}
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-10">
          {filteredTrades.length === 0 ? (
            <div className="col-span-full py-16 text-center bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-lg">
              <div className="flex flex-col items-center justify-center text-gray-500">
                <Filter size={32} className="mb-3 opacity-50" />
                <p className="text-base font-medium text-gray-400">Bu periyotta hiç işlem yapılmamış.</p>
                <p className="text-xs mt-1">Bot şu an piyasayı taramaya devam ediyor.</p>
              </div>
            </div>
          ) : (
            filteredTrades.map((log, i) => (
              <SignalCard key={log.id || i} trade={log} onClick={setActiveTrade} />
            ))
          )}
        </div>
      )}

      {activeTrade && (
        <ChartModal trade={activeTrade} onClose={() => setActiveTrade(null)} />
      )}
    </div>
  );
}
