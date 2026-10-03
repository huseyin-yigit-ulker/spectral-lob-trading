import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

export default function TradeLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchLogs() {
      const { data, error } = await supabase
        .from('trade_logs')
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
      <h2 className="text-2xl font-bold border-b border-gray-700 pb-2">Son İşlemler (Trade Logs)</h2>
      {loading ? (
        <p className="text-gray-400">Yükleniyor...</p>
      ) : (
        <div className="overflow-x-auto bg-gray-800 rounded-lg border border-gray-700 shadow-lg">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-900 text-gray-400">
              <tr>
                <th className="p-3">Zaman</th>
                <th className="p-3">Sembol</th>
                <th className="p-3">Sinyal</th>
                <th className="p-3">Fiyat</th>
                <th className="p-3">OBI</th>
                <th className="p-3">FVG Derinlik (%)</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="p-4 text-center text-gray-500">Henüz işlem bulunmuyor.</td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="border-t border-gray-700 hover:bg-gray-750">
                    <td className="p-3">{new Date(log.zaman).toLocaleString()}</td>
                    <td className="p-3 font-bold text-blue-400">{log.sembol}</td>
                    <td className="p-3">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${log.sinyal.includes('AL') ? 'bg-green-900 text-green-300' : log.sinyal.includes('SAT') ? 'bg-red-900 text-red-300' : 'bg-gray-700'}`}>
                        {log.sinyal}
                      </span>
                    </td>
                    <td className="p-3">{log.fiyat}</td>
                    <td className="p-3">{log.obi}</td>
                    <td className="p-3">{log.fvg_depth}</td>
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
