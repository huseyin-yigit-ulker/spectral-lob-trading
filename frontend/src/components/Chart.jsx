import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

export default function PnlChart({ data }) {
  const chartContainerRef = useRef();

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      height: 300,
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: '#F0B90B',
      topColor: 'rgba(240, 185, 11, 0.4)',
      bottomColor: 'rgba(240, 185, 11, 0.0)',
      lineWidth: 2,
    });

    // Transform data for chart: cumulative PnL over time
    // data should be sorted by time ascending
    let cumulative = 0;
    const chartData = [...data]
      .sort((a, b) => new Date(a.exit_time).getTime() - new Date(b.exit_time).getTime())
      .map(t => {
        cumulative += t.pnl_pct;
        return {
          time: new Date(t.exit_time).getTime() / 1000,
          value: cumulative
        };
      });

    // Ensure unique times
    const uniqueData = [];
    const seen = new Set();
    chartData.forEach(d => {
      if (!seen.has(d.time)) {
        seen.add(d.time);
        uniqueData.push(d);
      } else {
        uniqueData[uniqueData.length - 1].value = d.value;
      }
    });

    areaSeries.setData(uniqueData);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-full min-h-[300px]" />;
}
