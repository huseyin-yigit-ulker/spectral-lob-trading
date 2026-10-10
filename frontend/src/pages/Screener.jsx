import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { Clock, Activity, Zap } from 'lucide-react';
import Tooltip from '../components/Tooltip';

export default function Screener() {
  const [screenerData, setScreenerData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchScreener() {
      setLoading(true);
      const { data, error } = await supabase
        .from('active_screener')
        .select('updated_at, data')
        .eq('id', 1)
        .single();
      
      if (data && data.data) {
        setScreenerData({
          updated_at: data.updated_at,
          details: data.data.details || []
        });
      }
      setLoading(false);
    }
    fetchScreener();
    const interval = setInterval(fetchScreener, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 border-b border-[#1f2937] pb-6">
        <div>
          <h2 className="text-2xl font-black text-gray-100 tracking-tight flex items-center gap-2">
            <Activity className="text-[#F0B90B]" size={24} /> Market Scanner Heatmap
          </h2>
          <p className="text-sm text-gray-500 mt-1.5">Anlık Hacim, Spread ve FVG Uzaklığına Göre Canlı Isı Haritası</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#1E2329] border border-[#2B3139] rounded-lg">
          <Clock size={16} className="text-[#F0B90B]" />
          <span className="text-xs text-gray-400 font-mono">
            {screenerData ? new Date(screenerData.updated_at).toLocaleTimeString() : 'Bekleniyor...'}
          </span>
        </div>
      </div>
      
      {loading && !screenerData ? (
        <div className="flex justify-center py-20"><div className="w-8 h-8 border-4 border-[#F0B90B] border-t-transparent rounded-full animate-spin"></div></div>
      ) : screenerData?.details?.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-gray-500 py-20">
          <Zap size={32} className="mb-3 opacity-50" />
          <p className="text-base font-medium text-gray-400">Şu an FVG hedefine yakın coin bulunamadı.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {screenerData?.details
            .sort((a, b) => b.score - a.score)
            .map((coin, i) => {
            // Generate color intensity based on score (max expected around 300)
            const intensity = Math.min(100, (coin.score / 250) * 100);
            return (
              <div 
                key={i} 
                className="relative overflow-hidden rounded-xl border border-[#1f2937] p-4 flex flex-col justify-between h-32 hover:border-gray-500 transition-colors group cursor-default"
                style={{
                  background: `linear-gradient(135deg, rgba(34, 197, 94, ${intensity * 0.005}) 0%, #0b0e14 100%)`
                }}
              >
                <div className="flex justify-between items-start">
                  <span className="font-black text-white text-lg tracking-tight">{coin.symbol.replace('USDT', '')}</span>
                  <span className="text-[10px] bg-[#1E2329] px-1.5 py-0.5 rounded font-mono text-gray-400 border border-[#2B3139]">
                    {Number(coin.fvg_dist).toFixed(2)}% FVG
                  </span>
                </div>
                
                <div className="space-y-1 mt-4">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Vol</span>
                    <span className="text-gray-300 font-mono">{(coin.vol / 1000000).toFixed(0)}M</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Score</span>
                    <span className="text-[#F0B90B] font-mono font-bold">{Number(coin.score).toFixed(0)}</span>
                  </div>
                </div>
                
                {/* Hover overlay with details */}
                <div className="absolute inset-0 bg-[#121822] opacity-0 group-hover:opacity-100 transition-opacity p-4 flex flex-col justify-center items-center text-center">
                   <p className="text-xs text-gray-400 mb-1">Spread: %{Number(coin.spread).toFixed(3)}</p>
                   <p className="text-xs text-gray-400">Price: ${Number(coin.price).toFixed(4)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
