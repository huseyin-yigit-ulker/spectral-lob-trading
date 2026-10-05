import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabase';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';
import { reconstructTrades } from '../utils/tradeLogic';
import { Filter } from 'lucide-react';

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

  useEffect(() => {
    async function fetchLogs() {
      setLoading(true);
      // PnL ve islem butunlugu (Entry-Exit eslesmesi) bozulmamasi icin once tum veriyi cekiyoruz
      const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: true });
      if (data) {
        const parsed = reconstructTrades(data);
        setAllReconstructedTrades(parsed.allTrades);
      }
      setLoading(false);
    }
    fetchLogs();
  }, []);

  // Tarih filtresini (Frontend tarafinda) uygula
  const filteredTrades = useMemo(() => {
    if (period === 'all') return allReconstructedTrades;
    
    const now = new Date().getTime();
    let limitMs = 0;
    
    if (period === '24h') limitMs = 24 * 60 * 60 * 1000;
    else if (period === '7d') limitMs = 7 * 24 * 60 * 60 * 1000;
    else if (period === '30d') limitMs = 30 * 24 * 60 * 60 * 1000;

    return allReconstructedTrades.filter(t => {
      const tradeTime = new Date(t.giris_zaman).getTime();
      return (now - tradeTime) <= limitMs;
    });
  }, [allReconstructedTrades, period]);

  return (
    <div className="space-y-6 relative h-full flex flex-col">
      <div className="border-b border-[#1f2937] pb-4 flex flex-col md:flex-row md:justify-between md:items-end gap-4 shrink-0">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">Signal Terminal</h2>
          <p className="text-sm text-gray-500 mt-1">Live V5 SMC Execution Logs</p>
        </div>
        
        {/* Period Selector */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          <Filter size={14} className="text-gray-500 hidden md:block mr-1" />
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
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-10">
          {filteredTrades.length === 0 ? (
            <div className="col-span-full py-12 text-center text-gray-500 font-medium bg-[#0B0E11] border border-[#1f2937] rounded-xl">
              Seçilen tarih aralığında işlem bulunamadı.
            </div>
          ) : (
            filteredTrades.map((log, i) => (
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
