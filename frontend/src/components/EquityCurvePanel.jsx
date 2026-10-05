import { useId, useMemo } from 'react';

export default function EquityCurvePanel({ data }) {
  const gid = useId();

  // data = array of trade logs
  const model = useMemo(() => {
    if (!Array.isArray(data) || data.length < 2) return null;
    const cum = [];
    let c = 0, peak = 0, lo = 0, hi = 0;
    
    // Simulate some PnL based on OBI to make the chart look alive
    // In production, you would map this to actual closed PnL tracking
    [...data].reverse().forEach((s) => {
      const pnlMock = Number(s.obi) > 0 ? 0.5 : -0.2; // mock logic
      c += pnlMock;
      cum.push(c);
      if (c > peak) peak = c;
      if (c < lo) lo = c;
      if (c > hi) hi = c;
    });
    
    // ensure span is non-zero
    if (hi === lo) {
        hi += 1;
        lo -= 1;
    }

    return { cum, total: cum[cum.length - 1], peak, lo, hi };
  }, [data]);

  if (!model) {
      return (
          <div className="bg-[#0b0e14] border border-[#1f2937] rounded-xl p-6 shadow-xl h-[250px] flex items-center justify-center text-gray-500">
              Veri bekleniyor...
          </div>
      );
  }

  const { cum, total, peak, lo, hi } = model;
  const W = 1000, H = 150, pad = 10;
  const n = cum.length;
  const span = hi - lo;
  
  const x = (i) => (i / (n - 1)) * W;
  const y = (v) => H - pad - ((v - lo) / span) * (H - pad * 2);
  const zeroY = y(0);
  
  const linePts = cum.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const pos = total >= 0;
  const lineColor = pos ? '#0ECB81' : '#F6465D';
  const softColor = pos ? 'rgba(14, 203, 129, 0.2)' : 'rgba(246, 70, 93, 0.2)';

  return (
    <div className="bg-[#0B0E11] border border-[#1f2937] rounded-xl p-6 shadow-xl">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">Kümülatif PnL (Mock)</h3>
          <p className="text-xs text-gray-600 mt-1">Gerçek kapanış verisi eklendiğinde güncellenecektir</p>
        </div>
        <div className="text-right">
          <span className={`text-2xl font-black ${pos ? 'text-[#0ECB81]' : 'text-[#F6465D]'}`}>
            {pos ? '+' : ''}{total.toFixed(2)} R
          </span>
        </div>
      </div>
      
      <div className="relative w-full h-[150px]">
        <svg className="w-full h-full overflow-visible" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id={`eq-${gid}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={softColor} />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>
          <polygon 
            points={`0,${zeroY.toFixed(1)} ${linePts} ${W},${zeroY.toFixed(1)}`}
            fill={`url(#eq-${gid})`} 
          />
          <line 
            x1="0" y1={zeroY.toFixed(1)} x2={W} y2={zeroY.toFixed(1)}
            stroke="#2B3139" strokeDasharray="5 5" strokeWidth="2" vectorEffect="non-scaling-stroke" 
          />
          <polyline 
            points={linePts} 
            fill="none" stroke={lineColor} strokeWidth="2.5"
            strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" 
          />
        </svg>
      </div>
    </div>
  );
}
