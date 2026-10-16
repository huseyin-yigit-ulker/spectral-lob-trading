import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { calculateTransactions } from '../utils/transactions';
import { Activity, Target, ShieldAlert, Zap, Clock, ArrowRight, TrendingUp, TrendingDown, Layers } from 'lucide-react';
import PnlChart from '../components/Chart';
import { useLive } from '../context/LiveContext';

export default function Dashboard() {
  const [stats, setStats] = useState({ transactions: 0, active: 0, winRate: 0, pnl: 0, profitFactor: 0 });
  const [closedTransactions, setClosedTransactions] = useState([]);
  const [activeTransactions, setActiveTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState('v5_4'); // 'v5_4' (Optimize PROD) veya 'v5_3' (Canlı Baseline)
  const [rawLogs, setRawLogs] = useState([]);
  const { btcRegime } = useLive() || {};

  const processLogs = (logs, ver) => {
    if (!logs || logs.length === 0) return;
    const txs = calculateTransactions(logs, ver);
    setClosedTransactions(txs.closed);
    setActiveTransactions(txs.active);
    
    const wins = txs.closed.filter(t => t.win);
    const losses = txs.closed.filter(t => !t.win);
    
    const wr = txs.closed.length > 0 ? ((wins.length / txs.closed.length) * 100).toFixed(1) : 0;
    const totalPnl = txs.closed.reduce((acc, val) => acc + val.pnl_pct, 0).toFixed(2);
    
    const grossProfit = wins.reduce((acc, val) => acc + val.pnl_pct, 0);
    const grossLoss = Math.abs(losses.reduce((acc, val) => acc + val.pnl_pct, 0));
    const profitFactor = grossLoss > 0 ? (grossProfit / grossLoss).toFixed(2) : (grossProfit > 0 ? '∞' : 0);
    
    setStats({ 
      transactions: txs.closed.length, 
      active: txs.active.length,
      winRate: wr, 
      pnl: totalPnl,
      profitFactor
    });
  };

  useEffect(() => {
    async function fetchData() {
      if (typeof document !== 'undefined' && document.hidden) return;
      const { data: logsData } = await supabase
        .from('trade_logs')
        .select('*')
        .order('zaman', { ascending: true });
        
      if (logsData) {
        setRawLogs(logsData);
        processLogs(logsData, version);
      }

      setLoading(false);
    }
    
    fetchData();
    const interval = setInterval(fetchData, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  // Versiyon degistiginde aninda tekrar hesapla
  const handleVersionChange = (newVer) => {
    setVersion(newVer);
    processLogs(rawLogs, newVer);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between border-b border-[#1f2937] pb-4 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-black text-gray-100 tracking-tight">SMC Terminal <span className="text-[#F0B90B]">V5</span></h2>
            {/* Version Switcher Buttons */}
            <div className="flex items-center bg-[#0B0E11] p-1 rounded-xl border border-[#1f2937] shadow-inner">
              <button
                onClick={() => handleVersionChange('v5_4')}
                className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                  version === 'v5_4'
                    ? 'bg-[#F0B90B] text-black shadow-lg shadow-[#F0B90B]/20'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Zap size={14} className={version === 'v5_4' ? 'text-black' : 'text-[#F0B90B]'} />
                V5.4 PROD (Optimize)
              </button>
              <button
                onClick={() => handleVersionChange('v5_3')}
                className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all flex items-center gap-1.5 ${
                  version === 'v5_3'
                    ? 'bg-[#2B3139] text-[#F0B90B] shadow-md'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Clock size={14} />
                V5.3 Canlı (Baseline)
              </button>
            </div>
          </div>
          <p className="text-sm text-gray-500 mt-1">High-Frequency Trading & Smart Money Concepts</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {btcRegime?.regime === 'BEARISH' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/30 rounded-full">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              <span className="text-xs font-bold text-red-400">BTC MAKRO: 🔴 DÜŞÜŞ (SHORT AĞIRLIKLI)</span>
            </div>
          )}
          {btcRegime?.regime === 'BULLISH' && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-full">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-xs font-bold text-green-400">BTC MAKRO: 🟢 YÜKSELİŞ (LONG AĞIRLIKLI)</span>
            </div>
          )}
          {(!btcRegime?.regime || btcRegime?.regime === 'NEUTRAL') && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/30 rounded-full">
              <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
              <span className="text-xs font-bold text-yellow-400">BTC MAKRO: ⚪ NÖTR (HER İKİ YÖN)</span>
            </div>
          )}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            <span className="text-xs font-bold text-green-400">SNIPER MODE ACTIVE</span>
          </div>
        </div>
      </div>

      {/* Version Status Comparison Banner */}
      {version === 'v5_4' ? (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-[0_0_20px_rgba(16,185,129,0.05)]">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse"></div>
            <div>
              <div className="text-xs font-black text-emerald-300">
                ⚡ V5.4 OPTİMİZE PROD GÖRÜNÜMÜ AKTİF
              </div>
              <div className="text-[11px] text-emerald-400/80 mt-0.5">
                4H Makro Ayı Trend Filtresi, %1.50 FVG Tavanı ve %0.70 Sıkılaştırılmış Hard Stop uygulanmıştır. 22 riskli işlem filtrelendi.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] font-mono text-emerald-300 bg-emerald-500/20 border border-emerald-500/30 px-2.5 py-1 rounded font-black">
              PF: 2.41 (+1.27)
            </span>
            <span className="text-[11px] font-mono text-emerald-300 bg-emerald-500/20 border border-emerald-500/30 px-2.5 py-1 rounded font-black">
              4.5x PnL KAZANCI
            </span>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
            <div>
              <div className="text-xs font-black text-yellow-300">
                📜 V5.3 CANLI BASELINE GÖRÜNÜMÜ AKTİF
              </div>
              <div className="text-[11px] text-yellow-400/80 mt-0.5">
                Canlı botun geçmişte aldığı 60 işlemin ham gerçekleşme verileridir (Filtresiz ve gevşek %1.00 hard stop).
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[11px] font-mono text-yellow-300 bg-yellow-500/20 border border-yellow-500/30 px-2.5 py-1 rounded font-black">
              PF: 1.14
            </span>
            <span className="text-[11px] font-mono text-yellow-300 bg-yellow-500/20 border border-yellow-500/30 px-2.5 py-1 rounded font-black">
              ORİJİNAL HAM VERİ
            </span>
          </div>
        </div>
      )}
      
      {/* Market Regime & Expected Trade Direction Policy Card */}
      <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-4 md:p-5 shadow-lg">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          
          {/* BTC Price & Regime */}
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-black text-2xl shrink-0 ${
              btcRegime?.regime === 'BEARISH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
              btcRegime?.regime === 'BULLISH' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
              'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
            }`}>
              ₿
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Bitcoin Makro Rejimi</span>
                <span className={`px-2 py-0.5 rounded text-[11px] font-black uppercase tracking-wider ${
                  btcRegime?.regime === 'BEARISH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                  btcRegime?.regime === 'BULLISH' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                  'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                }`}>
                  {btcRegime?.regime === 'BEARISH' ? '🔴 DÜŞÜŞ TRENDİ (BEARISH)' : btcRegime?.regime === 'BULLISH' ? '🟢 YÜKSELİŞ TRENDİ (BULLISH)' : '⚪ YATAY (RANGE)'}
                </span>
              </div>
              <div className="text-lg font-black text-gray-100 mt-0.5 flex items-center gap-2">
                <span>{btcRegime?.price ? `$${Number(btcRegime.price).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}` : 'BTC Analiz Ediliyor'}</span>
                <span className="text-xs font-medium text-gray-500">(1H / 4H Trend Filtresi)</span>
              </div>
            </div>
          </div>

          {/* Trade Direction Policy */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 bg-[#0B0E11] px-3.5 py-2 rounded-lg border border-[#1f2937]">
              <span className="text-xs text-gray-400 font-semibold">LONG Sinyalleri:</span>
              {btcRegime?.regime === 'BEARISH' ? (
                <span className="text-xs font-black text-red-400 flex items-center gap-1">❌ BLOKE EDİLDİ</span>
              ) : (
                <span className="text-xs font-black text-green-400 flex items-center gap-1">✅ İZİNLİ</span>
              )}
            </div>

            <div className="flex items-center gap-2 bg-[#0B0E11] px-3.5 py-2 rounded-lg border border-[#1f2937]">
              <span className="text-xs text-gray-400 font-semibold">SHORT Sinyalleri:</span>
              {btcRegime?.regime === 'BULLISH' ? (
                <span className="text-xs font-black text-red-400 flex items-center gap-1">❌ BLOKE EDİLDİ</span>
              ) : (
                <span className="text-xs font-black text-green-400 flex items-center gap-1">✅ İZİNLİ (BEKLENEN)</span>
              )}
            </div>

            <div className="flex items-center gap-2 bg-[#0B0E11] px-3.5 py-2 rounded-lg border border-[#1f2937]">
              <span className="text-xs text-gray-400 font-semibold">Beklenen İşlem:</span>
              <span className={`text-xs font-black px-2 py-0.5 rounded ${
                btcRegime?.regime === 'BEARISH' ? 'bg-red-500/20 text-red-300' :
                btcRegime?.regime === 'BULLISH' ? 'bg-green-500/20 text-green-300' :
                'bg-yellow-500/20 text-yellow-300'
              }`}>
                {btcRegime?.regime === 'BEARISH' ? '🔻 SADECE SHORT' : btcRegime?.regime === 'BULLISH' ? '🔺 SADECE LONG' : '↔️ HER İKİ YÖN'}
              </span>
            </div>
          </div>

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
                  <div key={i} className="p-4 bg-green-500/5 rounded-lg border border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.1)] space-y-2">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-bold text-white flex items-center gap-2 text-lg">
                          {t.sembol}
                          <span className={`text-xs font-bold px-2 py-1 rounded flex items-center gap-1 ${t.tip === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                            {t.tip === 'LONG' ? <TrendingUp size={12}/> : <TrendingDown size={12}/>}
                            {t.tip}
                          </span>
                          {t.is_sniper && (
                            <span className="text-[10px] font-black px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                              🎯 SNİPER
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Giriş: ${Number(t.entry_price).toFixed(4)}</div>
                      </div>
                      <div className="text-right">
                         <div className="text-xs text-gray-400">₿ BTC: <span className="font-bold text-gray-200">{t.btc_regime || 'NEUTRAL'}</span></div>
                         <div className="text-xs text-green-400 mt-1 animate-pulse">SMC İzleniyor...</div>
                      </div>
                    </div>
                    {t.entry_reason && (
                      <div className="text-[10px] text-gray-400 bg-[#0B0E11]/60 px-2 py-1 rounded border border-[#1f2937]/50 truncate font-mono">
                        <span className="text-[#F0B90B] font-bold">Neden:</span> {t.entry_reason}
                      </div>
                    )}
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
              <div key={i} className={`p-3 rounded-lg border space-y-1.5 ${t.win ? 'bg-green-900/10 border-green-500/20' : 'bg-red-900/10 border-red-500/20'}`}>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-white text-sm">{t.sembol}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-1 ${t.tip === 'LONG' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {t.tip}
                    </span>
                    {t.is_sniper && (
                      <span className="text-[9px] font-bold px-1 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        🎯 Sniper
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] font-mono text-gray-400">
                    ₿ {t.btc_regime || 'NEUTRAL'}
                  </span>
                </div>
                <div className="flex justify-between text-xs text-gray-400">
                  <div>${Number(t.entry_price).toFixed(4)}</div>
                  <ArrowRight size={12} className="text-gray-600 mx-1"/>
                  <div>${Number(t.exit_price).toFixed(4)}</div>
                </div>
                {t.entry_reason && (
                  <div className="text-[10px] text-gray-400 truncate font-mono">
                    <span className="text-[#F0B90B]">Neden:</span> {t.entry_reason}
                  </div>
                )}
                <div className="flex justify-between items-end pt-0.5 border-t border-[#1f2937]/40">
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
