import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';
import { reconstructTrades, parseUtcDate } from '../utils/tradeLogic';
import { Filter, List, Activity, TrendingUp, TrendingDown, Target, Zap, Clock, ShieldCheck, AlertTriangle } from 'lucide-react';

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
  const [version] = useState('v5_5');
  const [rawLogs, setRawLogs] = useState([]);

  const processLogs = (data) => {
    if (!data) return;
    const parsed = reconstructTrades(data, 'v5_5');
    setAllReconstructedTrades(parsed.allTrades);
  };

  const fetchLogs = async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: true });
    if (data) {
      setRawLogs(data);
      processLogs(data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000);
    return () => clearInterval(interval);
  }, []);

  // 1. Periyoda göre zaman filtresi
  const periodTrades = useMemo(() => {
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

  // 2. Ekranda gösterilecek nihai işlemler (Yalnızca geçerli canlı işlemler)
  const displayedTrades = useMemo(() => {
    return periodTrades.filter(t => !t.is_filtered);
  }, [periodTrades]);

  // 3. Dinamik İstatistikler (Net ve Brüt)
  const periodStats = useMemo(() => {
    const targetTrades = displayedTrades;
    const closed = targetTrades.filter(t => t.status === 'CLOSED');
    const active = targetTrades.filter(t => t.status === 'OPEN');
    
    const MAKER_FEE = 0.04;
    const totalBrutPnl = closed.reduce((acc, t) => acc + (t.brut_pnl !== undefined ? t.brut_pnl : (t.pnl_yuzde || 0)), 0);
    const totalCommission = closed.length * MAKER_FEE;
    const totalNetPnl = totalBrutPnl - totalCommission;

    const netWins = closed.filter(t => (t.net_pnl !== undefined ? t.net_pnl : (t.pnl_yuzde - MAKER_FEE)) > 0);
    const brutWins = closed.filter(t => (t.brut_pnl !== undefined ? t.brut_pnl : t.pnl_yuzde) > 0);
    const netLosses = closed.filter(t => (t.net_pnl !== undefined ? t.net_pnl : (t.pnl_yuzde - MAKER_FEE)) <= 0);

    const netWinRate = closed.length > 0 ? (netWins.length / closed.length) * 100 : 0;
    const brutWinRate = closed.length > 0 ? (brutWins.length / closed.length) * 100 : 0;

    return {
      total: targetTrades.length,
      closedCount: closed.length,
      activeCount: active.length,
      netWins: netWins.length,
      netLosses: netLosses.length,
      brutWins: brutWins.length,
      netWinRate: netWinRate.toFixed(1),
      brutWinRate: brutWinRate.toFixed(1),
      totalNetPnl: totalNetPnl.toFixed(2),
      totalBrutPnl: totalBrutPnl.toFixed(2),
      totalCommission: totalCommission.toFixed(2),
    };
  }, [displayedTrades]);

  const versionLabel = 'V5.5';

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
        
        {/* Version Switcher & Segmented Period Filter */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Active Version Badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#0B0E11] border border-[#1f2937] shadow-inner">
            <Zap size={14} className="text-[#F0B90B]" />
            <span className="text-xs font-black text-gray-200">V5.5 Canlı PROD</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          </div>

          {/* Segmented Period Filter */}
          <div className="flex bg-[#121822] p-1 rounded-xl border border-[#1f2937] shadow-sm">
            <div className="flex bg-[#0B0E11] p-0.5 rounded-lg border border-[#1f2937]">
              {PERIODS.map(p => (
                <button
                  key={p.id}
                  onClick={() => setPeriod(p.id)}
                  className={`px-3.5 py-1.5 rounded-md text-xs font-bold transition-all whitespace-nowrap text-center ${
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
      </div>

      {/* Period Quick Stats Summary Bar (Çift Yönlü Net & Brüt Görünüm) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Toplam İşlem</span>
            <span className="text-lg font-black text-gray-100 font-mono">{periodStats.closedCount}</span>
            <span className="text-[10px] text-gray-400 ml-1.5 font-mono">
              kapalı {periodStats.activeCount > 0 ? `(${periodStats.activeCount} aktif)` : ''}
            </span>
          </div>
          <Zap size={20} className="text-[#F0B90B]/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Kazanma Oranı (WR)</span>
            <span className="text-lg font-black text-emerald-400 font-mono">%{periodStats.netWinRate}</span>
            <span className="text-[10px] text-gray-400 block font-mono">Brüt: %{periodStats.brutWinRate} ({periodStats.netWins}W / {periodStats.netLosses}L)</span>
          </div>
          <Target size={20} className="text-emerald-400/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Brüt PnL (Ham)</span>
            <span className={`text-lg font-black font-mono ${Number(periodStats.totalBrutPnl) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {Number(periodStats.totalBrutPnl) >= 0 ? '+' : ''}{periodStats.totalBrutPnl}%
            </span>
            <span className="text-[10px] text-gray-400 block font-mono">Komisyon: -%{periodStats.totalCommission}</span>
          </div>
          <TrendingUp size={20} className="text-blue-400/60" />
        </div>

        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between shadow-[0_0_15px_rgba(16,185,129,0.05)]">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Net PnL (Limit)</span>
            <span className={`text-lg font-black font-mono ${Number(periodStats.totalNetPnl) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {Number(periodStats.totalNetPnl) >= 0 ? '+' : ''}{periodStats.totalNetPnl}%
            </span>
            <span className="text-[10px] text-emerald-400/80 block font-mono">Maker -%0.04 Düşülmüş</span>
          </div>
          {Number(periodStats.totalNetPnl) >= 0 ? (
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
          {displayedTrades.length === 0 ? (
            <div className="col-span-full py-16 text-center bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-lg">
              <div className="flex flex-col items-center justify-center text-gray-500">
                <Filter size={32} className="mb-3 opacity-50" />
                <p className="text-base font-medium text-gray-400">Bu periyotta hiç işlem yapılmamış.</p>
                <p className="text-xs mt-1">Bot şu an piyasayı taramaya devam ediyor.</p>
              </div>
            </div>
          ) : (
            displayedTrades.map((log, i) => (
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
