import { Clock, Activity, CheckCircle2, CircleDashed, ArrowUpRight, ArrowDownRight, Timer, TrendingUp, TrendingDown, Layers, ChevronRight } from 'lucide-react';
import { formatUtcDateTime, formatUtcTime, formatSmartPrice } from '../utils/tradeLogic';

export default function SignalCard({ trade, onClick }) {
  const isLong = trade.yön === 'LONG';
  const isClosed = trade.status === 'CLOSED';
  const isWin = trade.pnl_yuzde > 0;
  
  const pnlFormatted = trade.pnl_yuzde !== undefined 
    ? `${trade.pnl_yuzde >= 0 ? '+' : ''}${trade.pnl_yuzde.toFixed(2)}%` 
    : null;

  return (
    <button 
      onClick={() => onClick(trade)}
      className="w-full text-left bg-[#0B0E11] hover:bg-[#0f141c] border border-[#1f2937] hover:border-[#F0B90B]/60 rounded-xl p-4 transition-all duration-200 hover:shadow-xl hover:shadow-[#F0B90B]/5 group flex flex-col gap-3 relative overflow-hidden"
    >
      {/* Top Accent Strip */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${
        !isClosed 
          ? 'bg-gradient-to-r from-amber-500 to-yellow-300 animate-pulse' 
          : isWin 
            ? 'bg-gradient-to-r from-emerald-500 to-green-400' 
            : 'bg-gradient-to-r from-rose-500 to-red-400'
      }`} />

      {/* Card Header: Symbol & Direction & Status */}
      <div className="flex justify-between items-start gap-2 pt-1">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-lg font-black text-white tracking-tight font-mono">{trade.sembol}</span>
            <span className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[11px] uppercase font-black border ${
              isLong 
                ? 'bg-green-500/10 text-green-400 border-green-500/25' 
                : 'bg-red-500/10 text-red-400 border-red-500/25'
            }`}>
              {isLong ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
              {trade.yön}
            </span>
          </div>
          
          {/* UTC Entry Time */}
          <div className="flex items-center gap-1.5 text-[11px] text-gray-400 mt-1 font-mono">
            <Clock size={11} className="text-[#F0B90B] shrink-0" />
            <span className="text-gray-300 font-semibold">Giriş (UTC):</span>
            <span className="text-gray-300">{formatUtcDateTime(trade.giris_zaman)}</span>
          </div>
        </div>

        {/* Status Badge */}
        <div className="shrink-0 flex flex-col items-end gap-1">
          {isClosed ? (
            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold border font-mono ${
              isWin 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' 
                : 'bg-rose-500/15 text-rose-400 border-rose-500/30'
            }`}>
              <CheckCircle2 size={12} />
              {pnlFormatted}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
              AÇIK POZİSYON
            </span>
          )}

          {/* Duration info */}
          <span className="text-[10px] text-gray-500 flex items-center gap-1 font-mono">
            <Timer size={10} /> {trade.sure_str || (isClosed ? `${trade.sure_dk} dk` : 'Aktif')}
          </span>
        </div>
      </div>

      {/* BTC Macro & Entry Reason Tag Row */}
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        {/* BTC Macro Badge */}
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border font-mono ${
          trade.btc_regime === 'BEARISH'
            ? 'bg-red-500/10 text-red-400 border-red-500/20'
            : trade.btc_regime === 'BULLISH'
              ? 'bg-green-500/10 text-green-400 border-green-500/20'
              : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
        }`}>
          <span>₿</span> BTC: {trade.btc_regime || 'NEUTRAL'}
        </span>

        {/* Sniper or Trend Match Badge */}
        {trade.is_sniper || (trade.entry_reason || '').toLowerCase().includes('sniper') ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-black bg-purple-500/15 text-purple-300 border border-purple-500/30 font-mono shadow-[0_0_8px_rgba(168,85,247,0.15)]">
            🎯 SNİPER İSTİSNASI
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono">
            🛡️ TREND UYUMLU
          </span>
        )}
      </div>

      {/* Entry Reason Description */}
      {trade.entry_reason && (
        <div className="text-[11px] text-gray-300 bg-[#121822]/90 border border-[#1f2937] rounded-lg px-2.5 py-1.5 flex items-start gap-1.5 leading-snug">
          <span className="text-[#F0B90B] font-bold shrink-0">Neden:</span>
          <span className="text-gray-300 font-mono text-[10.5px] truncate" title={trade.entry_reason}>{trade.entry_reason}</span>
        </div>
      )}

      {/* Prices Grid: Entry & Exit */}
      <div className="grid grid-cols-2 gap-2 mt-0.5">
        {/* Entry Price Box */}
        <div className="bg-[#121822] rounded-lg p-2.5 border border-[#1f2937]/80">
          <div className="flex items-center justify-between text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">
            <span>Giriş Fiyatı</span>
            <span className="text-gray-500 font-mono text-[9px]">ENTRY</span>
          </div>
          <div className="font-mono text-sm font-semibold text-gray-100 flex items-center gap-1">
            <span className="text-[#F0B90B] text-xs">$</span>
            {formatSmartPrice(trade.giris_fiyat)}
          </div>
        </div>

        {/* Exit Price Box */}
        <div className={`rounded-lg p-2.5 border ${
          isClosed 
            ? isWin 
              ? 'bg-emerald-950/20 border-emerald-500/25' 
              : 'bg-rose-950/20 border-rose-500/25'
            : 'bg-[#121822] border-[#1f2937]/80'
        }`}>
          <div className="flex items-center justify-between text-[10px] uppercase font-bold tracking-wider mb-1">
            <span className={isClosed ? (isWin ? 'text-emerald-400' : 'text-rose-400') : 'text-gray-400'}>
              {isClosed ? 'Çıkış Fiyatı' : 'Çıkış Durumu'}
            </span>
            <span className="text-gray-500 font-mono text-[9px]">{isClosed ? 'EXIT' : 'LIVE'}</span>
          </div>
          <div className="font-mono text-sm font-semibold flex items-center gap-1">
            {isClosed ? (
              <>
                <span className={`text-xs ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>$</span>
                <span className={isWin ? 'text-emerald-200' : 'text-rose-200'}>
                  {formatSmartPrice(trade.cikis_fiyat)}
                </span>
              </>
            ) : (
              <span className="text-xs text-amber-400/90 font-sans italic flex items-center gap-1">
                <CircleDashed size={12} className="animate-spin" /> Takip Ediliyor
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Exit Time info if closed */}
      {isClosed && trade.cikis_zaman && (
        <div className="flex items-center justify-between text-[10px] text-gray-400 px-2 py-1 bg-[#121822]/60 rounded border border-[#1f2937]/50 font-mono">
          <span className="text-gray-500 flex items-center gap-1">
            <Clock size={10} /> Çıkış (UTC):
          </span>
          <span className="text-gray-300 font-medium">{formatUtcDateTime(trade.cikis_zaman)}</span>
        </div>
      )}

      {/* Bottom SMC & Order Flow Metrics */}
      <div className="grid grid-cols-3 gap-1.5 text-[11px] pt-1 border-t border-[#1f2937]/60 font-mono">
        {/* OBI */}
        <div className="bg-[#121822] px-2 py-1 rounded text-center border border-[#1f2937]/40">
          <span className="text-[9px] text-gray-500 block uppercase">OBI</span>
          <span className={`font-bold ${Number(trade.obi) > 0 ? 'text-emerald-400' : Number(trade.obi) < 0 ? 'text-rose-400' : 'text-gray-400'}`}>
            {Number(trade.obi) > 0 ? '+' : ''}{Number(trade.obi).toFixed(2)}
          </span>
        </div>

        {/* CVD */}
        <div className="bg-[#121822] px-2 py-1 rounded text-center border border-[#1f2937]/40">
          <span className="text-[9px] text-gray-500 block uppercase">CVD</span>
          <span className={`font-bold ${Number(trade.cvd) > 0 ? 'text-emerald-400' : Number(trade.cvd) < 0 ? 'text-rose-400' : 'text-gray-400'}`}>
            {Number(trade.cvd) > 0 ? '+' : ''}{Number(trade.cvd).toFixed(0)}
          </span>
        </div>

        {/* FVG Depth */}
        <div className="bg-[#121822] px-2 py-1 rounded text-center border border-[#1f2937]/40">
          <span className="text-[9px] text-gray-500 block uppercase">FVG DERİNLİK</span>
          <span className="text-cyan-400 font-bold">
            %{Number(trade.fvg_depth || 0).toFixed(2)}
          </span>
        </div>
      </div>

      {/* Footer hint */}
      <div className="flex items-center justify-between text-[10px] text-gray-500 group-hover:text-[#F0B90B] transition-colors pt-0.5">
        <span className="font-mono text-gray-500 text-[10px] truncate max-w-[170px]">
          {trade.context || 'SMC Context'}
        </span>
        <span className="flex items-center gap-0.5 font-bold">
          Grafiği İncele <ChevronRight size={11} className="transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>
    </button>
  );
}

