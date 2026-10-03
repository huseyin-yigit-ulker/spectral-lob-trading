import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function Screener() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      const { data } = await supabase.from('screener_history').select('*').order('id', { ascending: false }).limit(100);
      if (data) setLogs(data);
      setLoading(false);
    }
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-[#1f2937] pb-4">
        <h2 className="text-2xl font-black text-gray-100 tracking-tight">Market Scanner</h2>
        <p className="text-sm text-gray-500 mt-1">Live Volatility & FVG Proximity Screening</p>
      </div>
      
      {loading ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : (
        <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937]">
                <tr>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Time</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Asset</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Score</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Volume</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Spread</th>
                  <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">FVG Dist</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {logs.length === 0 ? (
                  <tr><td colSpan="7" className="px-6 py-12 text-center text-gray-500 font-medium">No scan data yet.</td></tr>
                ) : (
                  logs.map(log => (
                    <tr key={log.id} className="hover:bg-[#121822] transition-colors">
                      <td className="px-6 py-4 text-gray-400 font-mono text-xs flex items-center gap-2">
                        <Clock size={12} />
                        {new Date(log.zaman).toLocaleTimeString()}
                      </td>
                      <td className="px-6 py-4 font-bold text-gray-200">{log.sembol}</td>
                      <td className="px-6 py-4">
                        {log.durum === 'KABUL' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] uppercase font-black bg-green-500/10 text-[#0ECB81] border border-[#0ECB81]/20"><CheckCircle2 size={12}/> ACCEPT</span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] uppercase font-black bg-red-500/10 text-[#F6465D] border border-[#F6465D]/20"><XCircle size={12}/> REJECT</span>
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
