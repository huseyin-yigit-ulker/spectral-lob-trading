import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Clock, CheckCircle2, XCircle, Filter, Info, Activity } from 'lucide-react';
import Tooltip from '../components/Tooltip';

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
        const periodStartMs = Math.floor(now.getTime() / (15 * 60 * 1000)) * (15 * 60 * 1000);
        const past = new Date(periodStartMs).toISOString();
        query = query.gte('zaman', past);
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
      <div className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 border-b border-[#1f2937] pb-6">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight flex items-center gap-2">
            <Activity className="text-[#F0B90B]" size={24} /> Market Scanner
          </h2>
          <p className="text-sm text-gray-500 mt-1.5">Canlı Volatilite ve FVG (Adil Değer Boşluğu) Tarama Motoru</p>
        </div>
        
        {/* Production-Grade Segmented Filters */}
        <div className="flex flex-col md:flex-row items-center gap-3 bg-[#121822] p-1.5 rounded-xl border border-[#1f2937] shadow-sm overflow-x-auto w-full xl:w-auto">
          
          {/* Status Filter */}
          <div className="flex bg-[#0B0E11] p-1 rounded-lg border border-[#1f2937] shrink-0">
            {STATUSES.map(s => (
              <button
                key={s.id}
                onClick={() => setStatusFilter(s.id)}
                className={`px-4 py-2 rounded-md text-xs font-bold transition-all whitespace-nowrap ${
                  statusFilter === s.id 
                    ? 'bg-[#2B3139] text-[#F0B90B] shadow-md' 
                    : 'text-gray-500 hover:text-gray-300 hover:bg-[#1E2329]'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          
          <div className="hidden md:block w-px h-6 bg-[#2B3139] shrink-0"></div>
          
          {/* Period Filter */}
          <div className="flex bg-[#0B0E11] p-1 rounded-lg border border-[#1f2937] shrink-0">
            {PERIODS.map(p => (
              <button
                key={p.id}
                onClick={() => setPeriod(p.id)}
                className={`px-4 py-2 rounded-md text-xs font-bold transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  period === p.id 
                    ? 'bg-[#2B3139] text-[#F0B90B] shadow-md' 
                    : 'text-gray-500 hover:text-gray-300 hover:bg-[#1E2329]'
                }`}
              >
                {p.id === 'active' && <Clock size={12} className={period === 'active' ? 'text-[#F0B90B]' : 'text-gray-500'} />}
                {p.label}
              </button>
            ))}
          </div>

        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-2xl relative">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937]">
                <tr>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider">Zaman</th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider">Sembol</th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider">
                    <Tooltip text="KABUL: Coin hacimli, spready düşük ve bir FVG bölgesine çok yakın. (Bot bu coini izlemeye alır) 

RED: Coin hacimli ama şu an herhangi bir FVG bölgesinde değil veya şartları karşılamıyor.">
                      Durum <Info size={14} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Screener Algoritmasının coine verdiği volatilite ve hacim puanı. Genelde 100 üzeri skorlar işlem için idealdir.">
                      Skor <Info size={14} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Son 24 saatlik kümülatif işlem hacmi (Dolar bazında). Tahtadaki likiditeyi gösterir.">
                      Hacim <Info size={14} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Alış ve Satış fiyatı arasındaki fark. Çok yüksekse (örneğin %0.5) bot komisyon kaybını önlemek için coini reddeder.">
                      Spread <Info size={14} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                  <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                    <Tooltip text="Fiyatın en yakın FVG (Adil Değer Boşluğu) merkezine olan % uzaklığı. KABUL alabilmesi için çok yakın (%0.15 altı) olması istenir.">
                      FVG Mesafe <Info size={14} className="text-[#F0B90B]" />
                    </Tooltip>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]/50">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-16 text-center">
                      <div className="flex flex-col items-center justify-center text-gray-500">
                        <Filter size={32} className="mb-3 opacity-50" />
                        <p className="text-base font-medium text-gray-400">Bu kriterlere uygun veri bulunamadı</p>
                        <p className="text-xs mt-1">Farklı bir periyot veya durum filtresi seçmeyi deneyin.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id} className="hover:bg-[#1A2027] transition-colors group">
                      <td className="px-6 py-4 text-gray-400 font-mono text-xs flex items-center gap-2">
                        <Clock size={12} className="opacity-50 group-hover:opacity-100 transition-opacity" />
                        {new Date(log.zaman).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-black text-gray-200 tracking-wide">{log.sembol}</td>
                      <td className="px-6 py-4">
                        {log.durum === 'KABUL' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] uppercase font-black bg-green-500/10 text-[#0ECB81] border border-[#0ECB81]/20 shadow-[0_0_10px_rgba(14,203,129,0.1)]"><CheckCircle2 size={12}/> KABUL</span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] uppercase font-black bg-red-500/10 text-[#F6465D] border border-[#F6465D]/20"><XCircle size={12}/> RED</span>
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
