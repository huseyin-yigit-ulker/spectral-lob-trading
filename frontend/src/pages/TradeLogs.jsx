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
  const [version, setVersion] = useState('v5_5');
  const [showFiltered, setShowFiltered] = useState(false);
  const [rawLogs, setRawLogs] = useState([]);
  const [backtestLogs, setBacktestLogs] = useState([]);

  const processBacktest = (bt) => {
    if (!bt) return;
    const trades = bt.map(t => {
      const ms = parseUtcDate(t.cikis_zaman).getTime() - parseUtcDate(t.giris_zaman).getTime();
      const sure_dk = Math.max(0, Math.floor(ms / 60000));
      return {
        id: t.id,
        sembol: t.sembol,
        yön: t.tip,
        status: 'CLOSED',
        giris_zaman: t.giris_zaman,
        cikis_zaman: t.cikis_zaman,
        giris_fiyat: Number(t.giris_fiyat),
        cikis_fiyat: Number(t.cikis_fiyat),
        pnl_yuzde: Number(t.pnl_yuzde),
        win: Boolean(t.win),
        fvg_depth: Number(t.fvg_depth),
        btc_regime: t.btc_regime,
        entry_reason: t.entry_reason,
        exit_reason: t.cikis_nedeni,
        sure_str: sure_dk < 60 ? `${sure_dk} dk` : `${Math.floor(sure_dk / 60)}s ${sure_dk % 60}d`,
        version: 'Backtest',
        is_filtered: false
      };
    });
    setAllReconstructedTrades(trades);
  };

  const processLogs = (data, ver) => {
    if (!data) return;
    const parsed = reconstructTrades(data, ver);
    setAllReconstructedTrades(parsed.allTrades);
  };

  const fetchLogs = async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: true });
    if (data) {
      setRawLogs(data);
      if (version !== 'v5_4_backtest') {
        processLogs(data, version);
      }
    }

    const { data: btData } = await supabase.from('backtest_trades').select('*').order('giris_zaman', { ascending: false });
    if (btData) {
      setBacktestLogs(btData);
      if (version === 'v5_4_backtest') {
        processBacktest(btData);
      }
    }

    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleVersionChange = (newVer) => {
    setVersion(newVer);
    if (newVer === 'v5_4_backtest') {
      processBacktest(backtestLogs);
    } else {
      processLogs(rawLogs, newVer);
    }
  };

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

  // 2. Seçili periyotta filtrelenen (elenen) işlem sayısı (DİNAMİK)
  const filteredCount = useMemo(() => {
    return periodTrades.filter(t => t.is_filtered).length;
  }, [periodTrades]);

  // 3. Ekranda gösterilecek nihai işlemler (showFiltered kapalıysa elenenler gizlenir)
  const displayedTrades = useMemo(() => {
    if (!showFiltered && (version === 'v5_5' || version === 'v5_4')) {
      return periodTrades.filter(t => !t.is_filtered);
    }
    return periodTrades;
  }, [periodTrades, showFiltered, version]);

  // 4. Dinamik İstatistikler (Seçili filtreye ve versiyona göre anında güncellenir)
  const periodStats = useMemo(() => {
    // showFiltered açıksa tüm ekrandaki işlemler, kapalıysa yalnızca filtreden geçen gerçek işlemler
    const targetTrades = showFiltered
      ? periodTrades
      : periodTrades.filter(t => !t.is_filtered);

    const closed = targetTrades.filter(t => t.status === 'CLOSED');
    const active = targetTrades.filter(t => t.status === 'OPEN');
    const wins = closed.filter(t => t.pnl_yuzde > 0);
    const losses = closed.filter(t => t.pnl_yuzde <= 0);
    const totalPnl = closed.reduce((acc, t) => acc + (t.pnl_yuzde || 0), 0);
    const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;

    // Filtreleme sayesinde engellenen toplam zarar
    const eliminated = periodTrades.filter(t => t.is_filtered && t.status === 'CLOSED');
    const preventedLoss = eliminated.reduce((acc, t) => acc + (t.pnl_yuzde < 0 ? Math.abs(t.pnl_yuzde) : 0), 0);

    return {
      total: targetTrades.length,
      closedCount: closed.length,
      activeCount: active.length,
      filteredCount,
      preventedLoss: preventedLoss.toFixed(2),
      wins: wins.length,
      losses: losses.length,
      winRate: winRate.toFixed(1),
      totalPnl: totalPnl.toFixed(2),
    };
  }, [periodTrades, showFiltered, filteredCount]);

  const versionLabel = useMemo(() => {
    if (version === 'v5_5') return 'V5.5';
    if (version === 'v5_4') return 'V5.4';
    if (version === 'v5_3') return 'V5.3';
    return 'Backtest';
  }, [version]);

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
          {/* Version Switcher */}
          <div className="flex flex-wrap items-center bg-[#0B0E11] p-1 rounded-xl border border-[#1f2937] shadow-inner gap-1">
            <button
              onClick={() => handleVersionChange('v5_5')}
              className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                version === 'v5_5' 
                  ? 'bg-[#F0B90B] text-black shadow-md' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Zap size={13} className={version === 'v5_5' ? 'text-black' : 'text-[#F0B90B]'} />
              V5.5 Canlı (Maks PnL)
            </button>
            <button
              onClick={() => handleVersionChange('v5_4')}
              className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                version === 'v5_4' 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <ShieldCheck size={13} />
              V5.4 Canlı (Dinamik SMC)
            </button>
            <button
              onClick={() => handleVersionChange('v5_3')}
              className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                version === 'v5_3' 
                  ? 'bg-[#2B3139] text-[#F0B90B] shadow-md' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Clock size={13} />
              V5.3 Canlı (Baseline)
            </button>
            <button
              onClick={() => handleVersionChange('v5_4_backtest')}
              className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                version === 'v5_4_backtest' 
                  ? 'bg-purple-600 text-white shadow-md' 
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Target size={13} className={version === 'v5_4_backtest' ? 'text-white' : 'text-purple-400'} />
              14G Backtest (30 Coin)
            </button>
          </div>

          {/* Dinamik Elenen İşlemleri Gör / Gizle Butonu */}
          {(version === 'v5_5' || version === 'v5_4') && (
            <button
              onClick={() => setShowFiltered(!showFiltered)}
              className={`px-3 py-2 rounded-xl text-xs font-black border transition-all flex items-center gap-1.5 ${
                showFiltered 
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 shadow-sm' 
                  : 'bg-[#121822] text-gray-300 border-[#1f2937] hover:text-white hover:border-[#F0B90B]/50'
              }`}
            >
              {showFiltered ? (
                <>✓ Filtrelenenleri Gizle ({filteredCount})</>
              ) : (
                <>👁️ Elenen ({filteredCount}) İşlemi Gör</>
              )}
            </button>
          )}

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

      {/* Dinamik Bilgilendirme ve Filtre Kalkanı Bildirimi */}
      {showFiltered && filteredCount > 0 && (
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs text-purple-200">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-purple-400 shrink-0" />
            <span>
              <strong>Ham Sinyal Görünümü:</strong> {versionLabel} kalkanı tarafından elenen {filteredCount} adet riskli işlem listeye dahil edildi.
            </span>
          </div>
          {Number(periodStats.preventedLoss) > 0 && (
            <span className="font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded font-bold shrink-0">
              🛡️ +%{periodStats.preventedLoss} Kayıp Önlendi
            </span>
          )}
        </div>
      )}

      {/* Period Quick Stats Summary Bar (Tamamen Dinamik) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3 flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Toplam İşlem</span>
            <span className="text-lg font-black text-gray-100 font-mono">{periodStats.closedCount}</span>
            <span className="text-[10px] text-gray-500 ml-1.5 font-mono">
              kapalı{filteredCount > 0 && !showFiltered ? ` (${filteredCount} elendi)` : ''}
            </span>
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
            <span className="text-[10px] uppercase font-bold text-gray-500 block">Kazanma Oranı (WR)</span>
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
