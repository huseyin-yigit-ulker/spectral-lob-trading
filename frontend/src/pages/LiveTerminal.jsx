import { useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';
import { Activity, TerminalSquare, Wifi, Info } from 'lucide-react';

export default function LiveTerminal() {
  const [symbols, setSymbols] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [wsStatus, setWsStatus] = useState('CONNECTING');
  const wsRef = useRef(null);
  
  // OBI ve CVD hesaplamalari icin buffer (sadece referans olarak tutuyoruz, React state'i yormamak icin)
  const buffers = useRef({});

  // 1. KABUL goren sembolleri cek
  useEffect(() => {
    async function fetchSymbols() {
      // Son 4 saat icindeki KABUL alanlari getir
      const past = new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString();
      const { data } = await supabase
        .from('screener_history')
        .select('sembol')
        .eq('durum', 'KABUL')
        .gte('zaman', past);

      if (data) {
        // Benzersiz sembolleri al (En fazla ilk 15 tanesini izleyelim ki tarayici kasmasin)
        const unique = [...new Set(data.map(d => d.sembol.toLowerCase()))].slice(0, 15);
        setSymbols(unique);
        
        // Ilk state'i olustur
        const initMetrics = {};
        unique.forEach(sym => {
          initMetrics[sym] = { price: 0, obi: 0, cvd: 0 };
          buffers.current[sym] = {
            obi_arr: [],
            cvd_arr: [], // { time: ms, qty: num }
          };
        });
        setMetrics(initMetrics);
      }
    }
    fetchSymbols();
  }, []);

  // 2. WebSocket Baglantisini Kur
  useEffect(() => {
    if (symbols.length === 0) return;

    const wsUrl = 'wss://fstream.binance.com/stream';
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('CONNECTED');
      // Sembollere abone ol (Hem emir defteri hem de trades)
      const streams = [];
      symbols.forEach(sym => {
        streams.push(`${sym}@depth20@100ms`);
        streams.push(`${sym}@aggTrade`);
      });

      ws.send(JSON.stringify({
        method: "SUBSCRIBE",
        params: streams,
        id: 1
      }));
    };

    ws.onclose = () => setWsStatus('DISCONNECTED');
    ws.onerror = () => setWsStatus('ERROR');

    // Her mesaj geldiginde React state'i yormamak icin saniyede 2 kez (500ms) aralikla render alacagiz
    let lastRender = Date.now();
    let tempMetrics = {};

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (!data.stream) return;

      const [symBase, streamType] = data.stream.split('@');
      const sym = symBase;
      const d = data.data;

      if (!buffers.current[sym]) return;
      const buf = buffers.current[sym];

      if (streamType.includes('depth')) {
        // OBI Hesapla
        let b_qty = 0; let a_qty = 0;
        d.b.forEach(bid => b_qty += parseFloat(bid[1]));
        d.a.forEach(ask => a_qty += parseFloat(ask[1]));
        
        const raw_obi = (b_qty - a_qty) / (b_qty + a_qty + 0.00000001);
        buf.obi_arr.push(raw_obi);
        if (buf.obi_arr.length > 50) buf.obi_arr.shift(); // Son 50 tik'in ortalamasi
        
        const avg_obi = buf.obi_arr.reduce((a,b) => a+b, 0) / buf.obi_arr.length;
        if (!tempMetrics[sym]) tempMetrics[sym] = { ...metrics[sym] };
        tempMetrics[sym].obi = avg_obi;

      } else if (streamType === 'aggTrade') {
        // CVD Hesapla ve Fiyat Guncelle
        const price = parseFloat(d.p);
        const qty = parseFloat(d.q);
        const isMaker = d.m; // Maker true ise Satis (Kirmizi), false ise Alis (Yesil)
        const netQty = isMaker ? -qty : qty;
        
        const now = Date.now();
        buf.cvd_arr.push({ time: now, qty: netQty });
        
        // Sadece son 1 dakikalik (60000ms) tradeleri tut
        buf.cvd_arr = buf.cvd_arr.filter(t => (now - t.time) <= 60000);
        const cvd_1m = buf.cvd_arr.reduce((sum, t) => sum + t.qty, 0);

        if (!tempMetrics[sym]) tempMetrics[sym] = { ...metrics[sym] };
        tempMetrics[sym].price = price;
        tempMetrics[sym].cvd = cvd_1m;
      }

      // Throttled State Update (500ms)
      const now = Date.now();
      if (now - lastRender > 500) {
        setMetrics(prev => {
          const next = { ...prev };
          Object.keys(tempMetrics).forEach(k => {
            next[k] = { ...prev[k], ...tempMetrics[k] };
          });
          return next;
        });
        tempMetrics = {};
        lastRender = now;
      }
    };

    return () => {
      ws.close();
    };
  }, [symbols]);

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
