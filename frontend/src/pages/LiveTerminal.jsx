import { Activity, TerminalSquare, Wifi } from 'lucide-react';
import { useLive } from '../context/LiveContext';

export default function LiveTerminal() {
  const { symbols, metrics, wsStatus } = useLive();

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4 border-b border-[#1f2937] pb-6 shrink-0">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight flex items-center gap-2">
            <TerminalSquare className="text-[#F0B90B]" size={24} /> Live Terminal
          </h2>
          <p className="text-sm text-gray-500 mt-1.5">Screener'dan KABUL alan coinlerin canlı emir defteri verisi</p>
        </div>
        
        <div className="flex items-center gap-2 px-4 py-2 bg-[#121822] border border-[#1f2937] rounded-xl shadow-sm">
          {wsStatus === 'CONNECTED' ? (
            <Wifi size={16} className="text-[#0ECB81] animate-pulse" />
          ) : wsStatus === 'CONNECTING' ? (
            <Wifi size={16} className="text-[#F0B90B] animate-pulse" />
          ) : (
            <Wifi size={16} className="text-[#F6465D]" />
          )}
          <span className="text-xs font-bold text-gray-300">
            WS: {wsStatus}
          </span>
        </div>
      </div>

      <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-2xl overflow-hidden flex-1">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-[#121822] border-b border-[#1f2937]">
              <tr>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider">Sembol</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Fiyat</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Canlı OBI (Depth)</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">CVD (Son 1dk)</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Referans Durumu</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f2937]/50">
              {symbols.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500">
                      <Activity size={32} className="mb-3 opacity-50" />
                      <p className="text-base font-medium text-gray-400">Canlı izlenecek "KABUL" onaylı coin bulunamadı.</p>
                      <p className="text-xs mt-1">Screener yeni coinler bulduğunda burada belirecektir.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                symbols.map(sym => {
                  const m = metrics[sym] || { price: 0, obi: 0, cvd: 0 };
                  const isObiBullish = m.obi > 0;
                  const isObiBearish = m.obi < 0;
                  const isCvdBullish = m.cvd > 0;
                  
                  return (
                    <tr key={sym} className="hover:bg-[#1A2027] transition-colors font-mono">
                      <td className="px-6 py-5 font-black text-gray-200 tracking-wide uppercase">{sym}</td>
                      <td className="px-6 py-5 text-right text-gray-300">
                        {m.price ? Number(m.price).toPrecision(6) : 'Bekleniyor...'}
                      </td>
                      <td className="px-6 py-5 text-right font-bold">
                        {m.obi !== 0 ? (
                          <span className={isObiBullish ? 'text-[#0ECB81]' : isObiBearish ? 'text-[#F6465D]' : 'text-gray-400'}>
                            {m.obi > 0 ? '+' : ''}{m.obi.toFixed(3)}
                          </span>
                        ) : '...'}
                      </td>
                      <td className="px-6 py-5 text-right font-bold">
                        {m.cvd !== 0 ? (
                          <span className={isCvdBullish ? 'text-[#0ECB81]' : 'text-[#F6465D]'}>
                            {m.cvd > 0 ? '+' : ''}{m.cvd.toFixed(2)}
                          </span>
                        ) : '...'}
                      </td>
                      <td className="px-6 py-5 text-center">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] uppercase font-black bg-[#1E2329] text-gray-400 border border-[#2B3139]">
                          Screener Onaylı
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
