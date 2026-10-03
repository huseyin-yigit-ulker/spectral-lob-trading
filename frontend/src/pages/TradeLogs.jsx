import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { ArrowUpRight, ArrowDownRight, Clock } from 'lucide-react';

export default function TradeLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      const { data } = await supabase.from('trade_logs').select('*').order('id', { ascending: false }).limit(50);
      if (data) setLogs(data);
      setLoading(false);
    }
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#1f2937] pb-4 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight">Signal Terminal</h2>
          <p className="text-sm text-gray-500 mt-1">Live V5 SMC Execution Logs</p>
        </div>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937]">
                <tr>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Timestamp</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Symbol</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Signal</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Price</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">OBI</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">FVG Depth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {logs.length === 0 ? (
                  <tr><td colSpan="6" className="px-6 py-12 text-center text-gray-500 font-medium">Awaiting Signals...</td></tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id} className="hover:bg-[#121822] transition-colors">
                      <td className="px-6 py-4 text-gray-400 font-mono text-xs flex items-center gap-2">
                        <Clock size={14} />
                        {new Date(log.zaman).toLocaleTimeString()}
                      </td>
                      <td className="px-6 py-4 font-bold text-gray-200">{log.sembol}</td>
                      <td className="px-6 py-4">
                        <SignalBadge signal={log.sinyal} />
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-gray-300">{log.fiyat}</td>
                      <td className="px-6 py-4 text-right font-mono text-gray-400">{log.obi}</td>
                      <td className="px-6 py-4 text-right font-mono text-gray-400">{log.fvg_depth}%</td>
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

function SignalBadge({ signal }) {
  const isLong = signal.includes('AL') || signal.includes('LONG');
  const isShort = signal.includes('SAT') || signal.includes('SHORT');
  
  if (isLong) {
    return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-green-500/10 text-green-400 border border-green-500/20"><ArrowUpRight size={14} /> {signal}</span>;
  }
  if (isShort) {
    return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/20"><ArrowDownRight size={14} /> {signal}</span>;
  }
  return <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-gray-800 text-gray-400 border border-gray-700">{signal}</span>;
}
