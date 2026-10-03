import { Clock, Activity, CheckCircle2, CircleDashed } from 'lucide-react';

export default function SignalCard({ trade, onClick }) {
  const isLong = trade.yön === 'LONG';
  const isClosed = trade.status === 'CLOSED';
  const isWin = trade.pnl_yuzde > 0;
  
  const timeAgo = (dateStr) => {
    const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
    if (diff < 1) return 'Az önce';
    if (diff < 60) return `${diff} dk önce`;
    const hrs = Math.floor(diff / 60);
    if (hrs < 24) return `${hrs} sa ${diff % 60} dk önce`;
    return `${Math.floor(hrs / 24)} gün önce`;
  };

  const durationStr = isClosed 
    ? (trade.sure_dk < 60 ? `${trade.sure_dk} dk` : `${Math.floor(trade.sure_dk/60)}s ${trade.sure_dk%60}d`)
    : 'Aktif';

  return (
    <button 
      onClick={() => onClick(trade)}
      className="w-full text-left bg-[#0B0E11] border border-[#1f2937] hover:border-[#F0B90B] rounded-xl p-4 transition-all hover:shadow-lg group flex flex-col gap-3"
    >
      <div className="flex justify-between items-start">
        <div>
          <span className="text-lg font-black text-gray-100 tracking-tight block">{trade.sembol}</span>
          <span className="text-xs text-gray-500 flex items-center gap-1 mt-1 font-mono">
            <Clock size={12} /> {timeAgo(trade.giris_zaman)}
          </span>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`px-2 py-1 rounded text-[10px] uppercase font-black border ${
            isLong ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
          }`}>
            {trade.yön}
          </span>
          {isClosed ? (
            <span className={`flex items-center gap-1 text-[10px] font-bold ${isWin ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
              <CheckCircle2 size={10} /> KAPALI ({trade.pnl_yuzde > 0 ? '+' : ''}{trade.pnl_yuzde.toFixed(2)}%)
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-bold text-[#F0B90B]">
              <CircleDashed size={10} className="animate-spin" /> AÇIK
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm mt-2">
        <div className="bg-[#1E2329] rounded p-2 border border-[#2B3139]">
          <span className="text-gray-500 text-[10px] uppercase block mb-1">Giriş</span>
          <span className="font-mono text-gray-200">{Number(trade.giris_fiyat).toPrecision(5)}</span>
        </div>
        {isClosed ? (
          <div className="bg-[#1E2329] rounded p-2 border border-[#2B3139]">
            <span className="text-gray-500 text-[10px] uppercase block mb-1">Süre / PnL</span>
            <span className={`font-mono ${isWin ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
              {durationStr}
            </span>
          </div>
        ) : (
          <div className="bg-[#1E2329] rounded p-2 border border-[#2B3139]">
            <span className="text-gray-500 text-[10px] uppercase block mb-1 flex items-center gap-1">
              <Activity size={10} /> OBI
            </span>
            <span className={`font-mono ${Number(trade.obi) > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {Number(trade.obi) > 0 ? '+' : ''}{Number(trade.obi).toFixed(2)}
            </span>
          </div>
        )}
      </div>
    </button>
  );
}
