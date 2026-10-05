import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Clock, CheckCircle2, XCircle, Filter, Info } from 'lucide-react';

const PERIODS = [
  { id: 'active', label: 'Aktif Periyot' },
  { id: '1h', label: 'Son 1 Saat' },
  { id: '4h', label: 'Son 4 Saat' },
  { id: '24h', label: 'Son 24 Saat' },
  { id: 'all', label: 'Tümü' },
];

const STATUSES = [
  { id: 'ALL', label: 'Tüm Durumlar' },
  { id: 'KABUL', label: 'Sadece KABUL' },
  { id: 'RED', label: 'Sadece RED' },
];

const Tooltip = ({ text, children }) => (
  <div className="group relative inline-flex items-center gap-1 cursor-help">
    {children}
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-56 bg-[#1E2329] text-gray-300 text-[11px] p-2.5 rounded-lg border border-[#2B3139] shadow-2xl z-50 whitespace-normal normal-case leading-relaxed font-medium">
      {text}
    </div>
  </div>
);

export default function Screener() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('active');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    async function fetchLogs() {
      setLoading(true);
      let query = supabase.from('screener_history').select('*').order('id', { ascending: false });
      
      const now = new Date();
      if (period === 'active') {
        query = query.limit(100);
      } else if (period === '1h') {
        const past = new Date(now.getTime() - 1 * 60 * 60 * 1000).toISOString();
        query = query.gte('zaman', past).limit(500);
      } else if (period === '4h') {
        const past = new Date(now.getTime() - 4 * 60 * 60 * 1000).toISOString();
        query = query.gte('zaman', past).limit(1000);
      } else if (period === '24h') {
        const past = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
        query = query.gte('zaman', past).limit(2000);
      } else if (period === 'all') {
        query = query.limit(3000);
      }

      if (statusFilter !== 'ALL') {
        query = query.eq('durum', statusFilter);
      }

      const { data } = await query;
      if (data) setLogs(data);
      setLoading(false);
    }
    fetchLogs();
  }, [period, statusFilter]);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#1f2937] pb-4 flex flex-col xl:flex-row xl:justify-between xl:items-end gap-4">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">Market Scanner</h2>
          <p className="text-sm text-gray-500 mt-1">Live Volatility & FVG Proximity Screening</p>
        </div>
        
        {/* Filters */}
        <div className="flex flex-col md:flex-row items-start md:items-center gap-4 pb-1 md:pb-0">
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto">
            <Filter size={14} className="text-gray-500 hidden md:block mr-1" />
            {STATUSES.map(s => (
              <button
                key={s.id}
                onClick={() => setStatusFilter(s.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors whitespace-nowrap ${
                  statusFilter === s.id 
                    ? 'bg-[#1E2329] text-[#F0B90B] border border-[#2B3139]' 
                    : 'text-gray-400 hover:text-white hover:bg-[#121822] border border-transparent'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          
          <div className="hidden md:block w-px h-6 bg-[#1f2937]"></div>
          
          <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto">
            <Clock size={14} className="text-gray-500 hidden md:block mr-1" />
            {PERIODS.map(p => (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors whitespace-nowrap ${
                  period === p.id 
                    ? 'bg-[#1E2329] text-[#F0B90B] border border-[#2B3139]' 
                    : 'text-gray-400 hover:text-white hover:bg-[#121822] border border-transparent'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl pb-32">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937]">
                <tr>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Zaman</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Sembol</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">
                    <Tooltip text="KABUL: Coin hacimli, spready düşük ve bir FVG bölgesine çok yakın. (Bot bu coini izlemeye alır) | RED: Coin hacimli ama şu an herhangi bir FVG bölgesinde değil.">
                      Durum <Info size={12} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Screener Algoritmasının coine verdiği volatilite ve hacim puanı. Genelde 100 üzeri skorlar işlem için uygundur.">
                      Skor <Info size={12} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Son 24 saatlik kümülatif işlem hacmi (Dolar). Likiditeyi gösterir.">
                      Hacim <Info size={12} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Alış ve Satış tahtası arasındaki fiyat farkı. Çok yüksekse (örneğin %0.5) bot komisyon kaybını önlemek için coini reddeder.">
                      Spread <Info size={12} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Fiyatın en yakın FVG (Adil Değer Boşluğu) merkezine olan % uzaklığı. KABUL alabilmesi için çok yakın (%0.15 altı) olması istenir.">
                      FVG Mesafe <Info size={12} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {logs.length === 0 ? (
                  <tr><td colSpan="7" className="px-6 py-12 text-center text-gray-500 font-medium">Bu periyotta tarama verisi bulunamadı.</td></tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id} className="hover:bg-[#121822] transition-colors">
                      <td className="px-6 py-4 text-gray-400 font-mono text-xs flex items-center gap-2">
                        <Clock size={12} />
                        {new Date(log.zaman).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-bold text-gray-200">{log.sembol}</td>
                      <td className="px-6 py-4">
                        {log.durum === 'KABUL' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] uppercase font-black bg-green-500/10 text-[#0ECB81] border border-[#0ECB81]/20"><CheckCircle2 size={12}/> KABUL</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] uppercase font-black bg-red-500/10 text-[#F6465D] border border-[#F6465D]/20"><XCircle size={12}/> RED</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-[#F0B90B] font-bold">{Number(log.skor).toFixed(1)}</td>
                      <td className="px-6 py-4 text-right font-mono text-gray-400">${Number(log.hacim).toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                      <td className="px-6 py-4 text-right font-mono text-gray-400">{Number(log.spread).toFixed(4)}%</td>
                      <td className="px-6 py-4 text-right font-mono text-gray-400">{Number(log.fvg_mesafe_yuzde).toFixed(2)}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
