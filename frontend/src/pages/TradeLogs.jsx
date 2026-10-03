import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import SignalCard from '../components/SignalCard';
import ChartModal from '../components/ChartModal';

export default function TradeLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTrade, setActiveTrade] = useState(null);

  useEffect(() => {
    async function fetchLogs() {
      const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: false }).limit(50);
      if (data) setLogs(data);
      setLoading(false);
    }
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6 relative h-full flex flex-col">
      <div className="border-b border-[#1f2937] pb-4 flex justify-between items-center shrink-0">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">Signal Terminal</h2>
          <p className="text-sm text-gray-500 mt-1">Live V5 SMC Execution Logs</p>
        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-10">
          {logs.length === 0 ? (
            <div className="col-span-full py-12 text-center text-gray-500 font-medium bg-[#0B0E11] border border-[#1f2937] rounded-xl">
              Awaiting Signals...
            </div>
          ) : (
            logs.map(log => (
              <SignalCard key={log.id} trade={log} onClick={setActiveTrade} />
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
