import { X } from 'lucide-react';
import TradeChart from './TradeChart';

export default function ChartModal({ trade, onClose }) {
  if (!trade) return null;

  const isLong = (trade.yön === 'LONG') || (trade.sinyal || '').includes('AL') || (trade.sinyal || '').includes('LONG');
  const badgeClass = isLong 
    ? 'bg-green-500/10 text-green-400 border-green-500/20' 
    : 'bg-red-500/10 text-red-400 border-red-500/20';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 md:p-8">
      <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-2xl w-full max-w-6xl h-full flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1f2937] bg-[#121822]">
          <div className="flex items-center gap-4">
            <h2 className="text-2xl font-black text-white tracking-tight">{trade.sembol}</h2>
            <span className={`px-2.5 py-1 rounded text-xs font-bold border ${badgeClass}`}>
              {trade.yön || trade.sinyal}
            </span>
            <span className="text-gray-400 text-sm font-mono bg-[#1E2329] px-2 py-1 rounded border border-[#2B3139]">
              {new Date(trade.giris_zaman || trade.zaman).toLocaleString()}
            </span>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-[#1E2329] rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Chart Area */}
        <div className="flex-1 w-full bg-[#0B0E11] relative">
          <TradeChart trade={trade} />
        </div>

        {/* Footer Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-6 py-4 border-t border-[#1f2937] bg-[#121822]">
          <div>
            <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">Giriş Fiyatı</p>
            <p className="text-lg font-mono text-gray-200">{Number(trade.giris_fiyat || trade.fiyat).toLocaleString(undefined, {maximumFractionDigits:5})}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">OBI (Orderbook)</p>
            <p className={`text-lg font-mono ${Number(trade.obi) > 0 ? 'text-green-400' : 'text-red-400'}`}>
              {Number(trade.obi).toFixed(3)}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">FVG Derinliği</p>
            <p className="text-lg font-mono text-gray-200">{Number(trade.fvg_depth).toFixed(3)}%</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs font-bold uppercase tracking-wider">SMC Context</p>
            <p className="text-lg font-mono text-gray-200">{trade.context || 'N/A'}</p>
          </div>
        </div>

      </div>
    </div>
  );
}
