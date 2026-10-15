import { X, Clock, ArrowUpRight, ArrowDownRight, CheckCircle2, CircleDashed, Timer, TrendingUp, TrendingDown, Layers, Activity } from 'lucide-react';
import TradeChart from './TradeChart';
import { formatUtcDateTime, formatSmartPrice } from '../utils/tradeLogic';

export default function ChartModal({ trade, onClose }) {
  if (!trade) return null;

  const isLong = (trade.yön === 'LONG') || (trade.sinyal || '').includes('AL') || (trade.sinyal || '').includes('LONG');
  const isClosed = trade.status === 'CLOSED' || !!trade.cikis_zaman;
  const isWin = (trade.pnl_yuzde || 0) > 0;
  
  const pnlFormatted = trade.pnl_yuzde !== undefined 
    ? `${trade.pnl_yuzde >= 0 ? '+' : ''}${Number(trade.pnl_yuzde).toFixed(2)}%` 
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-3 md:p-6">
      <div className="bg-[#0B0E11] border border-[#1f2937] rounded-2xl shadow-2xl w-full max-w-7xl h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 px-6 py-4 border-b border-[#1f2937] bg-[#121822]">
          <div className="flex flex-wrap items-center gap-3">
            {/* Symbol */}
            <h2 className="text-2xl font-black text-white tracking-tight font-mono">{trade.sembol}</h2>
            
            {/* Direction Badge */}
            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-black uppercase border font-mono ${
              isLong 
                ? 'bg-green-500/10 text-green-400 border-green-500/30' 
                : 'bg-red-500/10 text-red-400 border-red-500/30'
            }`}>
              {isLong ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {trade.yön || (isLong ? 'LONG' : 'SHORT')}
            </span>

            {/* Status & PnL Badge */}
            {isClosed ? (
              <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-bold font-mono border ${
                isWin 
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' 
                  : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
              }`}>
                <CheckCircle2 size={13} />
                KAPALI ({pnlFormatted})
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                AÇIK POZİSYON
              </span>
            )}

            {/* Timestamps (UTC) in Header */}
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-gray-400 bg-[#1E2329]/80 px-3 py-1 rounded-lg border border-[#2B3139]">
              <span className="flex items-center gap-1 text-gray-300">
                <Clock size={12} className="text-[#F0B90B]" />
                <span className="text-gray-500">Giriş:</span> {formatUtcDateTime(trade.giris_zaman)}
              </span>
              {isClosed && trade.cikis_zaman && (
                <>
                  <span className="text-gray-600">|</span>
                  <span className="flex items-center gap-1 text-gray-300">
                    <span className="text-gray-500">Çıkış:</span> {formatUtcDateTime(trade.cikis_zaman)}
                  </span>
                </>
              )}
              <span className="text-gray-600">|</span>
              <span className="flex items-center gap-1 text-gray-400">
                <Timer size={12} /> {trade.sure_str || (isClosed ? `${trade.sure_dk} dk` : 'Aktif')}
              </span>
            </div>
          </div>

          {/* Close Button */}
          <button 
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-[#1E2329] rounded-lg transition-colors shrink-0 self-end sm:self-center"
            title="Kapat"
          >
            <X size={22} />
          </button>
        </div>

        {/* BTC Macro & Entry Reason Banner */}
        <div className="px-6 py-2 bg-[#0d121a] border-b border-[#1f2937] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-gray-400 font-bold uppercase text-[10px]">Giriş Analizi:</span>
            
            {/* BTC Regime */}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold border font-mono ${
              trade.btc_regime === 'BEARISH' 
                ? 'bg-red-500/10 text-red-400 border-red-500/30' 
                : trade.btc_regime === 'BULLISH' 
                  ? 'bg-green-500/10 text-green-400 border-green-500/30' 
                  : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
            }`}>
              <span>₿</span> BTC: {trade.btc_regime || 'NEUTRAL'}
            </span>

            {/* Sniper Exception or Trend Match */}
            {trade.is_sniper || (trade.entry_reason || '').toLowerCase().includes('sniper') ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-black bg-purple-500/20 text-purple-300 border border-purple-500/40 font-mono shadow-[0_0_10px_rgba(168,85,247,0.2)]">
                🎯 SNİPER İSTİSNASI (BTC'den Bağımsız)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
                🛡️ BTC Trend Uyumlu
              </span>
            )}

            {/* Entry Reason Description */}
            {trade.entry_reason && (
              <span className="text-gray-300 font-mono text-[11px] ml-1">
                <span className="text-gray-500 font-semibold">• Neden:</span> {trade.entry_reason}
              </span>
            )}
          </div>

          {/* Micro LOB metrics */}
          <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
            <span>Clean OBI: <strong className="text-gray-300">{trade.clean_obi ? Number(trade.clean_obi).toFixed(3) : '-'}</strong></span>
            <span>•</span>
            <span>RLR: <strong className="text-gray-300">{trade.rlr ? `%${(Number(trade.rlr)*100).toFixed(0)}` : '-'}</strong></span>
          </div>
        </div>

        {/* Chart Area */}
        <div className="flex-1 w-full bg-[#0B0E11] relative overflow-hidden">
          <TradeChart trade={trade} />
        </div>

        {/* Detailed Footer Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 px-6 py-3.5 border-t border-[#1f2937] bg-[#121822]">
          {/* Giriş Fiyatı */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Giriş Fiyatı</p>
            <p className="text-sm font-black font-mono text-gray-100 mt-0.5">
              ${formatSmartPrice(trade.giris_fiyat || trade.fiyat)}
            </p>
          </div>

          {/* Çıkış Fiyatı */}
          <div className={`p-2 rounded-lg border ${
            isClosed 
              ? isWin 
                ? 'bg-emerald-950/20 border-emerald-500/25' 
                : 'bg-rose-950/20 border-rose-500/25'
              : 'bg-[#0B0E11] border-[#1f2937]/70'
          }`}>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Çıkış Fiyatı</p>
            <p className={`text-sm font-black font-mono mt-0.5 ${
              isClosed 
                ? isWin ? 'text-emerald-300' : 'text-rose-300'
                : 'text-amber-400 text-xs italic font-sans'
            }`}>
              {isClosed ? `$${formatSmartPrice(trade.cikis_fiyat)}` : 'Pozisyon Açık'}
            </p>
          </div>

          {/* Net PnL */}
          <div className={`p-2 rounded-lg border ${
            isClosed 
              ? isWin 
                ? 'bg-emerald-950/20 border-emerald-500/25' 
                : 'bg-rose-950/20 border-rose-500/25'
              : 'bg-[#0B0E11] border-[#1f2937]/70'
          }`}>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Net PnL</p>
            <p className={`text-sm font-black font-mono mt-0.5 ${
              isClosed 
                ? isWin ? 'text-emerald-400' : 'text-rose-400'
                : 'text-gray-400'
            }`}>
              {isClosed ? pnlFormatted : 'İzleniyor'}
            </p>
          </div>

          {/* İşlem Süresi */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">İşlem Süresi</p>
            <p className="text-sm font-bold font-mono text-gray-200 mt-0.5">
              {trade.sure_str || (isClosed ? `${trade.sure_dk} dk` : 'Aktif')}
            </p>
          </div>

          {/* OBI */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">Orderbook OBI</p>
            <p className={`text-sm font-bold font-mono mt-0.5 ${Number(trade.obi) > 0 ? 'text-emerald-400' : Number(trade.obi) < 0 ? 'text-rose-400' : 'text-gray-300'}`}>
              {Number(trade.obi) > 0 ? '+' : ''}{Number(trade.obi || 0).toFixed(3)}
            </p>
          </div>

          {/* CVD */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">CVD (1m)</p>
            <p className={`text-sm font-bold font-mono mt-0.5 ${Number(trade.cvd) > 0 ? 'text-emerald-400' : Number(trade.cvd) < 0 ? 'text-rose-400' : 'text-gray-300'}`}>
              {Number(trade.cvd) > 0 ? '+' : ''}{Number(trade.cvd || 0).toFixed(0)}
            </p>
          </div>

          {/* FVG Derinliği */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">FVG Derinlik</p>
            <p className="text-sm font-bold font-mono text-cyan-400 mt-0.5">
              %{Number(trade.fvg_depth || 0).toFixed(3)}
            </p>
          </div>

          {/* SMC Context */}
          <div className="bg-[#0B0E11] p-2 rounded-lg border border-[#1f2937]/70">
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-wider">SMC Context</p>
            <p className="text-xs font-bold font-mono text-gray-200 mt-1 truncate" title={trade.context}>
              {trade.context || 'NEUTRAL'}
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

