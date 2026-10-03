import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

export default function Screener() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      const { data, error } = await supabase
        .from('screener_history')
        .select('*')
        .order('id', { ascending: false })
        .limit(100);
      
      if (!error && data) {
        setLogs(data);
      }
      setLoading(false);
    }
    fetchLogs();
  }, []);

  return (
    <div className="space-y-4 mt-4">
      <h2 className="text-2xl font-bold border-b border-gray-700 pb-2">İzci Geçmişi (Screener)</h2>
      {loading ? (
        <p className="text-gray-400">Yükleniyor...</p>
      ) : (
        <div className="overflow-x-auto bg-gray-800 rounded-lg border border-gray-700 shadow-lg">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900 text-gray-400">
              <tr>
                <th className="p-3">Zaman</th>
                <th className="p-3">Sembol</th>
                <th className="p-3">Durum</th>
                <th className="p-3">Skor</th>
                <th className="p-3">Hacim</th>
                <th className="p-3">Spread</th>
                <th className="p-3">FVG Mesafe (%)</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="p-4 text-center text-gray-500">Henüz tarama verisi yok.</td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{new Date(log.zaman).toLocaleString()}</td>
                    <td className="p-3 font-bold text-yellow-400">{log.sembol}</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${log.durum === 'KABUL' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                        {log.durum}
                      </span>
                    </td>
                    <td className="p-3">{log.skor}</td>
                    <td className="p-3">{Number(log.hacim).toLocaleString()}</td>
                    <td className="p-3">{log.spread}</td>
                    <td className="p-3">{log.fvg_mesafe_yuzde}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
