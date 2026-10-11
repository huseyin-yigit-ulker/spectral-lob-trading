import { useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, createSeriesMarkers } from 'lightweight-charts';
import { readChartTheme } from '../utils/chartTheme';
import { formatSmartPrice, formatUtcDateTime } from '../utils/tradeLogic';

const norm = (s) => (s ? s.replace(/[^A-Za-z0-9]/g, '') : '');

function getPrecisionAndMinMove(samplePrice) {
  const p = Number(samplePrice) || 1;
  let precision = 2;
  if (p < 0.0001) precision = 7;
  else if (p < 0.01) precision = 6;
  else if (p < 1) precision = 5;
  else if (p < 10) precision = 4;
  else if (p < 1000) precision = 2;
  const minMove = Math.pow(10, -precision);
  return { precision, minMove };
}

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
      grid: {
        vertLines: { color: 'rgba(43, 49, 57, 0.4)' },
        horzLines: { color: 'rgba(43, 49, 57, 0.4)' },
      },
      width: el.clientWidth,
      height: el.clientHeight || 450,
      rightPriceScale: {
        borderColor: th.border,
        scaleMargins: { top: 0.15, bottom: 0.15 },
        autoScale: true,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: th.border,
        tickMarkFormatter: (time) => {
          const date = new Date(time * 1000);
          const h = String(date.getUTCHours()).padStart(2, '0');
          const m = String(date.getUTCMinutes()).padStart(2, '0');
          return `${h}:${m}`;
        },
      },
      crosshair: { mode: 1 },
    });

    const isLong = (trade.yön === 'LONG') || (trade.sinyal || '').includes('AL') || (trade.sinyal || '').includes('LONG');
    const isClosed = trade.status === 'CLOSED' || !!trade.cikis_zaman;
    const isWin = (trade.pnl_yuzde || 0) > 0;
    const entryPrice = Number(trade.giris_fiyat || trade.fiyat);
    const exitPrice = Number(trade.cikis_fiyat);

    const { precision, minMove } = getPrecisionAndMinMove(entryPrice);

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: th.up,
      downColor: th.down,
      borderVisible: false,
      wickUpColor: th.up,
      wickDownColor: th.down,
      priceFormat: {
        type: 'price',
        precision: precision,
        minMove: minMove,
      },
    });

    (async () => {
      try {
        setStatus('Binance mum verileri çekiliyor...');
        const entryTimeMs = new Date(trade.giris_zaman || trade.zaman).getTime();
        const exitTimeMs = trade.cikis_zaman ? new Date(trade.cikis_zaman).getTime() : entryTimeMs;
        
        // Giriş ve çıkış anını rahatça kapsayacak zaman penceresi (1.5 saat öncesi - 1.5 saat sonrası)
        const padBefore = 90 * 60 * 1000;
        const padAfter = 90 * 60 * 1000;
        const from = entryTimeMs - padBefore;
        const to = Math.min(Date.now(), Math.max(exitTimeMs + padAfter, entryTimeMs + padAfter));

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
          setStatus('Grafik mum verisi bulunamadı');
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

        // --- GİRİŞ & ÇIKIŞ MARKERLARI ---
        const entrySec = Math.floor(entryTimeMs / 1000);
        let bestEntryTime = candles[0]?.time || entrySec;
        for (const c of candles) {
          if (c.time <= entrySec) bestEntryTime = c.time;
          else break;
        }

        const markers = [
          {
            time: bestEntryTime,
            position: isLong ? 'belowBar' : 'aboveBar',
            shape: isLong ? 'arrowUp' : 'arrowDown',
            color: '#F0B90B',
            size: 2,
            text: `GİRİŞ ${isLong ? 'LONG' : 'SHORT'} ($${formatSmartPrice(entryPrice)})`,
          },
        ];

        // Eğer işlem kapandıysa ÇIKIŞ noktası işaretini de ekle
        if (isClosed && trade.cikis_zaman) {
          const exitSec = Math.floor(exitTimeMs / 1000);
          let bestExitTime = null;
          for (const c of candles) {
            if (c.time <= exitSec) bestExitTime = c.time;
            else break;
          }
          if (!bestExitTime && candles.length > 0) {
            bestExitTime = candles[candles.length - 1].time;
          }

          if (bestExitTime) {
            const pnlStr = trade.pnl_yuzde !== undefined ? `${trade.pnl_yuzde >= 0 ? '+' : ''}${trade.pnl_yuzde.toFixed(2)}%` : '';
            markers.push({
              time: bestExitTime,
              position: isLong ? 'aboveBar' : 'belowBar',
              shape: 'circle',
              color: isWin ? '#0ECB81' : '#F6465D',
              size: 2,
              text: `ÇIKIŞ ($${formatSmartPrice(exitPrice)}) ${pnlStr}`,
            });
          }
        }

        markers.sort((a, b) => a.time - b.time);
        createSeriesMarkers(candle, markers);

        // --- GİRİŞ FİYAT ÇİZGİSİ ---
        if (Number.isFinite(entryPrice) && entryPrice > 0) {
          candle.createPriceLine({
            price: entryPrice,
            color: '#F0B90B',
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: true,
            title: `GİRİŞ ($${formatSmartPrice(entryPrice)})`,
          });
        }

        // --- ÇIKIŞ FİYAT ÇİZGİSİ ---
        if (isClosed && Number.isFinite(exitPrice) && exitPrice > 0) {
          candle.createPriceLine({
            price: exitPrice,
            color: isWin ? '#0ECB81' : '#F6465D',
            lineWidth: 2,
            lineStyle: 2, // Dashed
            axisLabelVisible: true,
            title: `ÇIKIŞ ($${formatSmartPrice(exitPrice)})`,
          });
        }

        // --- FVG LİKİDİTE BÖLGELERİ ---
        const fvgTop = Number(trade.fvg_top);
        const fvgBottom = Number(trade.fvg_bottom);
        if (Number.isFinite(fvgTop) && fvgTop > 0) {
          candle.createPriceLine({
            price: fvgTop,
            color: 'rgba(14, 203, 129, 0.5)',
            lineWidth: 1,
            lineStyle: 3,
            axisLabelVisible: true,
            title: `FVG Top ($${formatSmartPrice(fvgTop)})`,
          });
        }
        if (Number.isFinite(fvgBottom) && fvgBottom > 0) {
          candle.createPriceLine({
            price: fvgBottom,
            color: 'rgba(246, 70, 93, 0.5)',
            lineWidth: 1,
            lineStyle: 3,
            axisLabelVisible: true,
            title: `FVG Bot ($${formatSmartPrice(fvgBottom)})`,
          });
        }

        chart.timeScale().fitContent();
        setStatus('');
      } catch {
        if (!cancelled) setStatus('Grafik verisi yüklenemedi');
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
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 440 }}>
      {status && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#848E9C', fontSize: 14, zIndex: 2,
          backgroundColor: 'rgba(11, 14, 17, 0.6)',
        }}>
          {status}
        </div>
      )}
      <div ref={ref} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}

