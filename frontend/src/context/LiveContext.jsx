import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { supabase } from '../lib/supabase';

const LiveContext = createContext();

export function LiveProvider({ children }) {
  const [symbols, setSymbols] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [wsStatus, setWsStatus] = useState('CONNECTING');
  const [activePeriodString, setActivePeriodString] = useState('');
  
  const wsRef = useRef(null);
  const buffers = useRef({});

  useEffect(() => {
    async function fetchSymbols() {
      const now = new Date();
      // 15 dakikalik periyodun baslangicini bul (ornegin 14:12 -> 14:00)
      const periodStartMs = Math.floor(now.getTime() / (15 * 60 * 1000)) * (15 * 60 * 1000);
      const periodStart = new Date(periodStartMs);
      
      const endMs = periodStartMs + (15 * 60 * 1000);
      const periodEnd = new Date(endMs);
      
      const pad = n => n.toString().padStart(2, '0');
      const pStr = `${pad(periodStart.getHours())}:${pad(periodStart.getMinutes())} - ${pad(periodEnd.getHours())}:${pad(periodEnd.getMinutes())}`;
      setActivePeriodString(pStr);

      const pastISO = periodStart.toISOString();

      const { data } = await supabase
        .from('screener_history')
        .select('sembol')
        .eq('durum', 'KABUL')
        .gte('zaman', pastISO);

      if (data) {
        const unique = [...new Set(data.map(d => d.sembol.toLowerCase()))].slice(0, 15);
        setSymbols(unique);
        
        const initMetrics = {};
        unique.forEach(sym => {
          initMetrics[sym] = { price: 0, obi: 0, cvd: 0 };
          buffers.current[sym] = { obi_arr: [], cvd_arr: [] };
        });
        setMetrics(initMetrics);

        if (unique.length > 0) {
          try {
            const symsString = JSON.stringify(unique.map(s => s.toUpperCase()));
            const res = await fetch(`https://fapi.binance.com/fapi/v1/ticker/price?symbols=${symsString}`);
            const prices = await res.json();
            
            setMetrics(prev => {
              const next = { ...prev };
              prices.forEach(p => {
                const s = p.symbol.toLowerCase();
                if (next[s]) next[s].price = parseFloat(p.price);
              });
              return next;
            });
          } catch(e) {}
        }
      }
    }
    
    fetchSymbols();
    
    // Screener yeni periyotta calistiginda hizla yakalamasi icin 1 dakikada bir kontrol et
    const interval = setInterval(fetchSymbols, 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (symbols.length === 0) return;
    
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsUrl = 'wss://fstream.binance.com/stream';
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('CONNECTED');
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
        let b_qty = 0; let a_qty = 0;
        d.b.forEach(bid => b_qty += parseFloat(bid[1]));
        d.a.forEach(ask => a_qty += parseFloat(ask[1]));
        
        const raw_obi = (b_qty - a_qty) / (b_qty + a_qty + 0.00000001);
        buf.obi_arr.push(raw_obi);
        if (buf.obi_arr.length > 50) buf.obi_arr.shift();
        
        const avg_obi = buf.obi_arr.reduce((a,b) => a+b, 0) / buf.obi_arr.length;
        if (!tempMetrics[sym]) tempMetrics[sym] = {};
        tempMetrics[sym].obi = avg_obi;

      } else if (streamType === 'aggTrade') {
        const price = parseFloat(d.p);
        const qty = parseFloat(d.q);
        const isMaker = d.m; 
        
        // USD cinsinden hesapla (Miktar * Fiyat) boylece BTC gibi pahali coinlerde CVD 0 kalmaz
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

    return () => {
      ws.close();
    };
  }, [symbols]);

  return (
    <LiveContext.Provider value={{ symbols, metrics, wsStatus, activePeriodString }}>
      {children}
    </LiveContext.Provider>
  );
}

export function useLive() {
  return useContext(LiveContext);
}
