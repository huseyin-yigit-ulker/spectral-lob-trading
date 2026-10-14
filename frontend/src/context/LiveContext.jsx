import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';

const LiveContext = createContext();

export function LiveProvider({ children }) {
  const [symbols, setSymbols] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [wsStatus, setWsStatus] = useState('CONNECTING');
  const [activePeriodString, setActivePeriodString] = useState('');
  const [btcRegime, setBtcRegime] = useState({ regime: 'NEUTRAL', price: 0 });
  
  const wsRef = useRef(null);
  const buffers = useRef({});
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    let isSubscribed = true;

    async function fetchSymbols() {
      if (typeof document !== 'undefined' && document.hidden) return;
      let unique = [];
      let updatedTime = null;

      try {
        // 1. active_screener tablosundan en güncel listeyi al
        const { data, error } = await supabase
          .from('active_screener')
          .select('updated_at, data')
          .eq('id', 1)
          .single();

        if (error) {
          console.warn('[LiveContext] active_screener query error:', error);
        }

        if (data) {
          if (data.updated_at) {
            updatedTime = new Date(data.updated_at);
          }
          let payload = data.data;
          if (typeof payload === 'string') {
            try {
              payload = JSON.parse(payload);
            } catch (e) {
              console.error('[LiveContext] JSON parse error:', e);
            }
          }

          if (payload) {
            let list = [];
            if (Array.isArray(payload.symbols) && payload.symbols.length > 0) {
              list = payload.symbols;
            } else if (Array.isArray(payload.details) && payload.details.length > 0) {
              list = payload.details.map(d => d.symbol || d.sembol);
            }

            if (list.length > 0) {
              unique = [...new Set(list.filter(Boolean).map(s => String(s).toLowerCase()))].slice(0, 15);
            }
          }
        }
      } catch (err) {
        console.error('[LiveContext] Error fetching active_screener:', err);
      }

      // 2. Eğer active_screener boş ise screener_history fallback
      if (unique.length === 0) {
        try {
          const { data: histData } = await supabase
            .from('screener_history')
            .select('sembol')
            .eq('durum', 'KABUL')
            .order('id', { ascending: false })
            .limit(15);
          if (histData && histData.length > 0) {
            unique = [...new Set(histData.map(d => d.sembol.toLowerCase()))].slice(0, 15);
          }
        } catch (e) {
          console.error('[LiveContext] screener_history fallback error:', e);
        }
      }

      // 3. Veritabanından hiçbir şey dönmezse popüler coinleri yedek olarak kullan (ekran asla boş kalmasın)
      if (unique.length === 0) {
        unique = ['btcusdt', 'ethusdt', 'solusdt', 'dogeusdt', 'xrpusdt'];
      }

      if (!isSubscribed) return;

      // Periyot zamanı formatlama (UTC)
      const now = updatedTime || new Date();
      const periodStartMs = Math.floor(now.getTime() / (15 * 60 * 1000)) * (15 * 60 * 1000);
      const periodStart = new Date(periodStartMs);
      const endMs = periodStartMs + (15 * 60 * 1000);
      const periodEnd = new Date(endMs);
      
      const pad = n => n.toString().padStart(2, '0');
      const pStr = `${pad(periodStart.getUTCHours())}:${pad(periodStart.getUTCMinutes())} - ${pad(periodEnd.getUTCHours())}:${pad(periodEnd.getUTCMinutes())} UTC`;
      setActivePeriodString(pStr);

      // Buffer'ları hazırla (mevcut olanları koru, yeni coinler ekle)
      unique.forEach(sym => {
        if (!buffers.current[sym]) {
          buffers.current[sym] = { obi_arr: [], cvd_arr: [] };
        }
      });

      // Metrics objesinde yeni sembolleri başlat
      setMetrics(prev => {
        const next = { ...prev };
        let changed = false;
        unique.forEach(sym => {
          if (!next[sym]) {
            next[sym] = { price: 0, obi: 0, cvd: 0 };
            changed = true;
          }
        });
        return changed ? next : prev;
      });

      // Sadece sembol listesi değiştiyse setSymbols tetikle (sürekli reconnect yapmaması için)
      setSymbols(prev => {
        if (prev.length === unique.length && prev.every((s, i) => s === unique[i])) {
          return prev;
        }
        return unique;
      });

      // İlk fiyatları Binance REST API'den hızlıca çek
      if (unique.length > 0) {
        try {
          const symsString = JSON.stringify(unique.map(s => s.toUpperCase()));
          const res = await fetch(`https://fapi.binance.com/fapi/v1/ticker/price?symbols=${symsString}`);
          const prices = await res.json();
          
          if (Array.isArray(prices) && isSubscribed) {
            setMetrics(prev => {
              const next = { ...prev };
              prices.forEach(p => {
                const s = p.symbol.toLowerCase();
                if (next[s] && next[s].price === 0) {
                  next[s] = { ...next[s], price: parseFloat(p.price) };
                }
              });
              return next;
            });
          }
        } catch(e) {}
      }
    }
    
    fetchSymbols();
    const interval = setInterval(fetchSymbols, 15 * 1000);
    return () => {
      isSubscribed = false;
      clearInterval(interval);
    };
  }, []);

  // SMC Canlı Metriklerini çek
  useEffect(() => {
    if (symbols.length === 0) return;
    let isSubscribed = true;
    
    async function fetchSMC() {
      if (typeof document !== 'undefined' && document.hidden) return;
      try {
        const { data } = await supabase
          .from('live_metrics')
          .select('*');
          
        if (data && isSubscribed) {
          const btcRow = data.find(d => (d.sembol || '').toLowerCase() === '_btc_');
          if (btcRow) {
            setBtcRegime({
              regime: btcRow.smc_status || 'NEUTRAL',
              price: parseFloat(btcRow.fvg_depth || 0)
            });
          }

          setMetrics(prev => {
            const next = { ...prev };
            data.forEach(d => {
              const s = (d.sembol || '').toLowerCase();
              if (s !== '_btc_' && next[s]) {
                next[s] = {
                  ...next[s],
                  smc_status: d.smc_status,
                  fvg_depth: parseFloat(d.fvg_depth || 0)
                };
              }
            });
            return next;
          });
        }
      } catch (e) {
        console.error('[LiveContext] fetchSMC error:', e);
      }
    }
    
    fetchSMC();
    const interval = setInterval(fetchSMC, 10000); // 10 saniyede bir

    const handleVisibility = () => {
      if (!document.hidden) fetchSMC();
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      isSubscribed = false;
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [symbols]);

  // Binance WebSocket Bağlantısı
  useEffect(() => {
    if (symbols.length === 0) {
      setWsStatus('DISCONNECTED');
      return;
    }
    
    let isUnmounted = false;

    function connectWebSocket() {
      if (isUnmounted) return;

      if (wsRef.current) {
        wsRef.current.close();
      }

      setWsStatus('CONNECTING');
      const wsUrl = 'wss://fstream.binance.com/stream';
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmounted) return;
        setWsStatus('CONNECTED');
        const streams = [];
        symbols.forEach(sym => {
          streams.push(`${sym}@depth20@100ms`);
          streams.push(`${sym}@trade`);
        });

        ws.send(JSON.stringify({
          method: "SUBSCRIBE",
          params: streams,
          id: 1
        }));
      };

      ws.onclose = () => {
        if (isUnmounted) return;
        setWsStatus('DISCONNECTED');
        // 3 saniye sonra otomatik yeniden bağlan
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (err) => {
        console.warn('[LiveContext WS error]', err);
        setWsStatus('ERROR');
      };

      let lastRender = Date.now();
      let tempMetrics = {};

      ws.onmessage = (event) => {
        if (isUnmounted) return;
        let msgData;
        try {
          msgData = JSON.parse(event.data);
        } catch (e) {
          return;
        }

        if (!msgData.stream) return;

        const [symBase, streamType] = msgData.stream.split('@');
        const sym = symBase.toLowerCase();
        const d = msgData.data;

        if (!buffers.current[sym]) {
          buffers.current[sym] = { obi_arr: [], cvd_arr: [] };
        }
        const buf = buffers.current[sym];

        if (streamType && streamType.includes('depth') && d.b && d.a) {
          let b_qty = 0; 
          let a_qty = 0;
          d.b.forEach(bid => { b_qty += parseFloat(bid[1]); });
          d.a.forEach(ask => { a_qty += parseFloat(ask[1]); });
          
          const raw_obi = (b_qty - a_qty) / (b_qty + a_qty + 0.00000001);
          buf.obi_arr.push(raw_obi);
          if (buf.obi_arr.length > 50) buf.obi_arr.shift();
          
          const avg_obi = buf.obi_arr.reduce((a,b) => a+b, 0) / buf.obi_arr.length;
          if (!tempMetrics[sym]) tempMetrics[sym] = {};
          tempMetrics[sym].obi = avg_obi;

        } else if (streamType === 'trade' && d.p && d.q) {
          const price = parseFloat(d.p);
          const qty = parseFloat(d.q);
          const isMaker = d.m; 
          
          const usdVolume = qty * price;
          const netUsd = isMaker ? -usdVolume : usdVolume;
          
          const now = Date.now();
          buf.cvd_arr.push({ time: now, qty: netUsd });
          
          buf.cvd_arr = buf.cvd_arr.filter(t => (now - t.time) <= 60000);
          const cvd_1m = buf.cvd_arr.reduce((sum, t) => sum + t.qty, 0);

          if (!tempMetrics[sym]) tempMetrics[sym] = {};
          tempMetrics[sym].price = price;
          tempMetrics[sym].cvd = cvd_1m;
        }

        const now = Date.now();
        if (now - lastRender > 500) {
          if (Object.keys(tempMetrics).length > 0) {
            setMetrics(prev => {
              const next = { ...prev };
              Object.keys(tempMetrics).forEach(k => {
                next[k] = { ...prev[k], ...tempMetrics[k] };
              });
              return next;
            });
            tempMetrics = {};
          }
          lastRender = now;
        }
      };
    }

    connectWebSocket();

    return () => {
      isUnmounted = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [symbols]);

  return (
    <LiveContext.Provider value={{ symbols, metrics, wsStatus, activePeriodString, btcRegime }}>
      {children}
    </LiveContext.Provider>
  );
}

export function useLive() {
  return useContext(LiveContext);
}
