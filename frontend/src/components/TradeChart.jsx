import { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, createSeriesMarkers, BaselineSeries } from 'lightweight-charts';
import { readChartTheme } from '../utils/chartTheme';

const norm = (s) => (s ? s.replace(/[^A-Za-z0-9]/g, '') : '');

export default function TradeChart({ trade }) {
  const ref = useRef(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!ref.current || !trade) return undefined;
    const el = ref.current;
    const th = readChartTheme();
    let cancelled = false;

    const chart = createChart(el, {
      layout: {
        background: { type: 'solid', color: th.bg },
        textColor: th.text,
        fontFamily: "'JetBrains Mono', 'SF Mono', Consolas, monospace",
      },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      width: el.clientWidth,
      height: el.clientHeight || 400,
      rightPriceScale: { borderColor: th.border, scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: th.border },
      crosshair: { mode: 1 },
    });

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: th.up, downColor: th.down, borderVisible: false,
      wickUpColor: th.up, wickDownColor: th.down,
    });

    // Islem bolgesi renklendirmesi icin Baseline Series
    const isLong = trade.yön === 'LONG';
    const areaSeries = chart.addSeries(BaselineSeries, {
      baseValue: { type: 'price', price: trade.giris_fiyat },
      lineWidth: 1, lineStyle: 2, priceLineVisible: false, 
      lastValueVisible: false, crosshairMarkerVisible: false,
      topLineColor: isLong ? th.up : 'transparent',
      topFillColor1: isLong ? th.upSoft(0.1) : 'transparent',
      topFillColor2: isLong ? th.upSoft(0.02) : 'transparent',
      bottomLineColor: isLong ? 'transparent' : th.down,
      bottomFillColor1: isLong ? 'transparent' : th.downSoft(0.1),
      bottomFillColor2: isLong ? 'transparent' : th.downSoft(0.02)
    });

    (async () => {
      try {
        setStatus('Grafik yukleniyor...');
        
        const entryMs = new Date(trade.giris_zaman).getTime();
        const exitMs = trade.cikis_zaman ? new Date(trade.cikis_zaman).getTime() : Date.now();
        
        const pad = Math.max(2 * 3600e3, (exitMs - entryMs) * 0.2); // Dinamik padding
        const from = entryMs - pad;
        const to = Math.min(Date.now(), exitMs + pad);

        const symbol = norm(trade.sembol);
        const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1m&startTime=${from}&endTime=${to}&limit=1500`;

        let raw = await (await fetch(url)).json();
        if (!Array.isArray(raw)) {
          const spotUrl = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1m&startTime=${from}&endTime=${to}&limit=1500`;
          raw = await (await fetch(spotUrl)).json();
        }

        if (cancelled) return;
        if (!Array.isArray(raw) || raw.length === 0) {
          setStatus('Grafik yuklenemedi');
          return;
        }

        const candles = raw.map((d) => ({
          time: d[0] / 1000, open: +d[1], high: +d[2], low: +d[3], close: +d[4]
        }));
        candle.setData(candles);

        // Zaman noktasina en yakin mumu bulma fonksiyonu
        const snap = (ms) => {
          const target = ms / 1000;
          let best = candles[0].time;
          for (const c of candles) { if (c.time <= target) best = c.time; else break; }
          return best;
        };

        const entrySec = snap(entryMs);
        const exitSec = trade.cikis_zaman ? snap(exitMs) : (candles.length ? candles[candles.length - 1].time : entrySec);

        // Marker'lar
        const markers = [];
        markers.push({
          time: entrySec, position: isLong ? 'belowBar' : 'aboveBar',
          shape: isLong ? 'arrowUp' : 'arrowDown', color: th.accent, size: 2, text: trade.yön
        });

        if (trade.cikis_zaman) {
          const isWin = trade.pnl_yuzde > 0;
          markers.push({
            time: exitSec, position: isLong ? 'aboveBar' : 'belowBar',
            shape: 'circle', size: 1, color: isWin ? th.up : th.down,
            text: `Çıkış (${trade.pnl_yuzde > 0 ? '+' : ''}${trade.pnl_yuzde.toFixed(2)}%)`
          });
        }
        
        markers.sort((a, b) => a.time - b.time);
        if (markers.length) createSeriesMarkers(candle, markers);

        // ict-trade benzeri Islem Alani Cizimi
        const zoneTop = trade.cikis_zaman ? trade.cikis_fiyat : (candles.length ? candles[candles.length-1].close : trade.giris_fiyat);
        areaSeries.setData([
          { time: entrySec, value: zoneTop },
          { time: exitSec, value: zoneTop }
        ]);

        // FVG Cizgileri
        if (trade.fvg_top > 0) candle.createPriceLine({ price: trade.fvg_top, color: th.upSoft(0.6), lineWidth: 1, lineStyle: 2 });
        if (trade.fvg_bottom > 0) candle.createPriceLine({ price: trade.fvg_bottom, color: th.downSoft(0.6), lineWidth: 1, lineStyle: 2 });
        candle.createPriceLine({ price: trade.giris_fiyat, color: th.accent, lineWidth: 1, lineStyle: 0 });

        chart.timeScale().fitContent();
        setStatus('');
      } catch {
        if (!cancelled) setStatus('Grafik yuklenemedi');
      }
    })();

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);

    return () => { cancelled = true; ro.disconnect(); chart.remove(); };
  }, [trade]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 400 }}>
      {status && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#848E9C', fontSize: 14, zIndex: 2 }}>
          {status}
        </div>
      )}
      <div ref={ref} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
