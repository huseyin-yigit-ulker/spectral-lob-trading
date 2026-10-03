import { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, createSeriesMarkers } from 'lightweight-charts';
import { readChartTheme } from '../utils/chartTheme';

// Sinyal grafigi — Binance'den 1m mumlar cekip giris/cikis oklarini ve
// FVG bolgesini gosterir. ict-trade/TradeChart.jsx'den adapte edilmistir.

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
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: th.border,
      },
      crosshair: { mode: 1 },
    });

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: th.up,
      downColor: th.down,
      borderVisible: false,
      wickUpColor: th.up,
      wickDownColor: th.down,
    });

    (async () => {
      try {
        setStatus('Grafik yukleniyor...');
        const tradeTime = new Date(trade.zaman).getTime();
        const pad = 2 * 3600e3; // 2 saat oncesi/sonrasi
        const from = tradeTime - pad;
        const to = Math.min(Date.now(), tradeTime + pad);

        const symbol = norm(trade.sembol);
        const url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1m&startTime=${from}&endTime=${to}&limit=1500`;

        let raw = await (await fetch(url)).json();
        if (!Array.isArray(raw)) {
          // Futures yoksa Spot dene
          const spotUrl = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=1m&startTime=${from}&endTime=${to}&limit=1500`;
          raw = await (await fetch(spotUrl)).json();
        }

        if (cancelled) return;
        if (!Array.isArray(raw) || raw.length === 0) {
          setStatus('Grafik yuklenemedi');
          return;
        }

        const candles = raw.map((d) => ({
          time: d[0] / 1000,
          open: +d[1],
          high: +d[2],
          low: +d[3],
          close: +d[4],
        }));
        candle.setData(candles);

        // Giris noktasi isareti
        const isLong = (trade.sinyal || '').includes('AL') || (trade.sinyal || '').includes('LONG');
        const tradeSec = Math.floor(tradeTime / 1000);
        let bestTime = candles[0]?.time || tradeSec;
        for (const c of candles) {
          if (c.time <= tradeSec) bestTime = c.time;
          else break;
        }

        const markers = [
          {
            time: bestTime,
            position: isLong ? 'belowBar' : 'aboveBar',
            shape: isLong ? 'arrowUp' : 'arrowDown',
            color: th.accent,
            size: 2,
            text: isLong ? 'LONG' : 'SHORT',
          },
        ];

        createSeriesMarkers(candle, markers);

        // FVG bolge cizgileri
        const fvgTop = Number(trade.fvg_top);
        const fvgBottom = Number(trade.fvg_bottom);
        if (Number.isFinite(fvgTop) && fvgTop > 0) {
          candle.createPriceLine({
            price: fvgTop,
            color: th.upSoft(0.6),
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'FVG Top',
          });
        }
        if (Number.isFinite(fvgBottom) && fvgBottom > 0) {
          candle.createPriceLine({
            price: fvgBottom,
            color: th.downSoft(0.6),
            lineWidth: 1,
            lineStyle: 2,
            axisLabelVisible: true,
            title: 'FVG Bot',
          });
        }

        // Giris fiyati cizgisi
        const entryPrice = Number(trade.fiyat);
        if (Number.isFinite(entryPrice) && entryPrice > 0) {
          candle.createPriceLine({
            price: entryPrice,
            color: th.accent,
            lineWidth: 1,
            lineStyle: 0,
            axisLabelVisible: true,
            title: 'Giris',
          });
        }

        chart.timeScale().fitContent();
        setStatus('');
      } catch {
        if (!cancelled) setStatus('Grafik yuklenemedi');
      }
    })();

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);

    return () => {
      cancelled = true;
      ro.disconnect();
      chart.remove();
    };
  }, [trade]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 400 }}>
      {status && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#848E9C', fontSize: 14, zIndex: 2,
        }}>
          {status}
        </div>
      )}
      <div ref={ref} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
