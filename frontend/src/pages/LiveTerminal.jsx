import React, { useState, useEffect } from 'react';
import { Activity, TerminalSquare, Wifi, Info } from 'lucide-react';
import { useLive } from '../context/LiveContext';
import Tooltip from '../components/Tooltip';

export default function LiveTerminal() {
  const { symbols, metrics, wsStatus, activePeriodString, btcRegime } = useLive();
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  useEffect(() => {
    if (symbols.length === 0) {
      setSelectedSymbol(null);
    }
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
        
        <div className="flex flex-col md:flex-row items-end md:items-center gap-3">
          {/* BTC Macro Regime Pill */}
          <div className="px-3.5 py-1.5 bg-[#121822] border border-[#1f2937] rounded-xl shadow-sm flex items-center gap-2.5">
            <div className={`w-2.5 h-2.5 rounded-full ${
              btcRegime?.regime === 'BEARISH' ? 'bg-red-500 animate-pulse' :
              btcRegime?.regime === 'BULLISH' ? 'bg-green-500 animate-pulse' :
              'bg-yellow-500'
            }`} />
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                BTC BEKLENEN YÖN {btcRegime?.price ? `($${Number(btcRegime.price).toLocaleString('en-US', { maximumFractionDigits: 0 })})` : ''}
              </span>
              <span className={`text-xs font-black ${
                btcRegime?.regime === 'BEARISH' ? 'text-red-400' :
                btcRegime?.regime === 'BULLISH' ? 'text-green-400' :
                'text-yellow-400'
              }`}>
                {btcRegime?.regime === 'BEARISH' ? '🔻 SADECE SHORT' :
                 btcRegime?.regime === 'BULLISH' ? '🔺 SADECE LONG' :
                 '↔️ ÇİFT YÖN (NÖTR)'}
              </span>
            </div>
          </div>

          {/* Active Period Badge */}
          {activePeriodString && (
            <div className="px-3 py-2 bg-[#1E2329] border border-[#2B3139] rounded-xl shadow-sm">
              <span className="text-xs font-bold text-[#F0B90B]">
                PERİYOT: <span className="text-gray-300 ml-1">{activePeriodString}</span>
              </span>
            </div>
          )}

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
      </div>

      {/* Macro Regime Policy Notice Banner */}
      <div className={`px-4 py-3 rounded-xl border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs shrink-0 ${
        btcRegime?.regime === 'BEARISH' ? 'bg-red-500/10 border-red-500/25 text-red-200' :
        btcRegime?.regime === 'BULLISH' ? 'bg-green-500/10 border-green-500/25 text-green-200' :
        'bg-yellow-500/10 border-yellow-500/25 text-yellow-200'
      }`}>
        <div className="flex items-center gap-2.5">
          <Info size={16} className={
            btcRegime?.regime === 'BEARISH' ? 'text-red-400 shrink-0' :
            btcRegime?.regime === 'BULLISH' ? 'text-green-400 shrink-0' :
            'text-yellow-400 shrink-0'
          } />
          <span>
            {btcRegime?.regime === 'BEARISH' ? (
              <span><strong>Makro Filtre Devrede:</strong> Bitcoin 1H/4H trendi düşüş yönünde. Bot şu anda <strong>sadece SHORT</strong> yönlü işlemleri onaylar. Karşı trend LONG sinyalleri (Sniper OBI ≥ +0.70 harici) otomatik engellenir.</span>
            ) : btcRegime?.regime === 'BULLISH' ? (
              <span><strong>Makro Filtre Devrede:</strong> Bitcoin 1H/4H trendi yükseliş yönünde. Bot şu anda <strong>sadece LONG</strong> yönlü işlemleri onaylar. SHORT sinyalleri filtrelenir.</span>
            ) : (
              <span><strong>Makro Filtre Devrede:</strong> Bitcoin nötr / yatay konsolidasyon bölgesinde. Bot strateji kurallarına göre <strong>hem LONG hem de SHORT</strong> pozisyonları işleme alabilir.</span>
            )}
          </span>
        </div>
        <div className="shrink-0 font-mono text-[11px] bg-black/40 px-2.5 py-1 rounded-lg border border-white/10 font-bold text-gray-300">
          Aktif Politika: {btcRegime?.regime === 'BEARISH' ? 'SHORT ÖNCELİKLİ' : btcRegime?.regime === 'BULLISH' ? 'LONG ÖNCELİKLİ' : 'DENGELİ'}
        </div>
      </div>

      <div className="flex flex-col xl:flex-row gap-6 flex-1 min-h-[500px]">
        {/* Main Table */}
        <div className={`bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-2xl overflow-hidden flex-1 transition-all duration-300 ${selectedSymbol ? 'xl:w-[35%]' : 'w-full'}`}>
          <div className="overflow-x-auto h-full">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937]">
              <tr>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider">Sembol</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Fiyat</th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                  <Tooltip text={`Emir Defteri Dengesizliği (Order Book Imbalance). Limit emirlerdeki alıcı/satıcı baskısını ölçer.\n\nSİNYAL ŞARTI:\nLONG (AL) için: > +0.30\nSHORT (SAT) için: < -0.30`}>
                    Canlı OBI (Depth) <Info size={14} className="text-[#F0B90B]" />
                  </Tooltip>
                </th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                  <Tooltip text={`Kümülatif Hacim Deltası. Market (Piyasa) emirleriyle gerçekleşen anlık alım-satım baskısıdır.\n\nSİNYAL ŞARTI:\nLONG (AL) için: Pozitif (> 0)\nSHORT (SAT) için: Negatif (< 0)`}>
                    CVD (Son 1dk) <Info size={14} className="text-[#F0B90B]" />
                  </Tooltip>
                </th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                  <Tooltip text={`Smart Money Concepts (SMC) piyasa yönü.\n\nSİNYAL ŞARTI:\nLONG (AL) için: BULLISH_FVG\nSHORT (SAT) için: BEARISH_FVG`}>
                    SMC DURUMU <Info size={14} className="text-[#F0B90B]" />
                  </Tooltip>
                </th>
                <th className="px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">
                  <Tooltip text={`Fair Value Gap (Likidite Boşluğu) derinliği.\n\nSİNYAL ŞARTI:\nİki yön için de en az: %0.20`}>
                    FVG Derinlik <Info size={14} className="text-[#F0B90B]" />
                  </Tooltip>
                </th>
                <th className={`px-6 py-5 text-xs font-bold text-gray-500 uppercase tracking-wider text-center ${selectedSymbol ? 'hidden' : ''}`}>
                  <Tooltip text={`Screener algoritması tarafından FVG (Boşluk) derinliği ve konumu uygun görülüp izlemeye alınan coinleri temsil eder.\n\nİŞLEME GİRİŞ:\nOBI ve CVD şartları aynı anda onaylandığında bot otomatik olarak pozisyon açar.`}>
                    Referans Durumu <Info size={14} className="text-[#F0B90B]" />
                  </Tooltip>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f2937]/50">
              {symbols.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-16 text-center">
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
                  const isCvdBullish = m.cvd > 0;
                  const isCvdBearish = m.cvd < 0;
                  
                  // OBI Renklendirme Stratejisi
                  let obiClass = "text-gray-400";
                  if (m.obi >= 0.30) obiClass = "bg-[#0ECB81]/20 text-[#0ECB81] px-2 py-1 rounded shadow-[0_0_12px_rgba(14,203,129,0.4)]";
                  else if (m.obi > 0) obiClass = "text-[#0ECB81]";
                  else if (m.obi <= -0.30) obiClass = "bg-[#F6465D]/20 text-[#F6465D] px-2 py-1 rounded shadow-[0_0_12px_rgba(246,70,93,0.4)]";
                  else if (m.obi < 0) obiClass = "text-[#F6465D]";

                  // CVD Formatlama (K/M)
                  const formatCVD = (val) => {
                    if (val === undefined || val === 0) return '0.00';
                    const absVal = Math.abs(val);
                    let formatted = absVal.toFixed(0);
                    if (absVal >= 1000000) formatted = (absVal / 1000000).toFixed(2) + 'M';
                    else if (absVal >= 1000) formatted = (absVal / 1000).toFixed(1) + 'K';
                    
                    return (val > 0 ? '+' : val < 0 ? '-' : '') + '$' + formatted;
                  };
                  
                  return (
                    <tr 
                      key={sym} 
                      onClick={() => setSelectedSymbol(sym)}
                      className={`transition-colors font-mono cursor-pointer ${selectedSymbol === sym ? 'bg-[#1f2937]/70' : 'hover:bg-[#1A2027]'}`}
                    >
                      <td className="px-6 py-5 font-black text-gray-200 tracking-wide uppercase">
                        <div className="flex items-center gap-2">
                          {selectedSymbol === sym && <div className="w-1.5 h-1.5 rounded-full bg-[#0ECB81] animate-pulse" />}
                          {sym}
                        </div>
                      </td>
                      <td className="px-6 py-5 text-right text-gray-300">
                        {m.price ? Number(m.price).toPrecision(6) : 'Bekleniyor...'}
                      </td>
                      <td className="px-6 py-5 text-right font-bold">
                        {m.obi !== undefined ? (
                          <span className={`inline-block transition-all ${obiClass}`}>
                            {m.obi > 0 ? '+' : ''}{m.obi.toFixed(3)}
                          </span>
                        ) : '...'}
                      </td>
                      <td className="px-6 py-5 text-right font-bold">
                        {m.cvd !== undefined ? (
                          <span className={isCvdBullish ? 'text-[#0ECB81]' : isCvdBearish ? 'text-[#F6465D]' : 'text-gray-400'}>
                            {formatCVD(m.cvd)}
                          </span>
                        ) : '...'}
                      </td>
                      <td className="px-6 py-5 text-right font-medium text-xs">
                        {m?.smc_status ? (
                          <div className="flex flex-col items-end gap-1">
                            <span className={m.smc_status === 'BULLISH_FVG' ? 'text-[#0ECB81] font-bold' : m.smc_status === 'BEARISH_FVG' ? 'text-[#F6465D] font-bold' : 'text-gray-400'}>
                              {m.smc_status}
                            </span>
                            {btcRegime?.regime === 'BEARISH' && m.smc_status === 'BEARISH_FVG' && (
                              <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded font-bold border border-green-500/20">
                                🎯 İzinli (Trend Yönü)
                              </span>
                            )}
                            {btcRegime?.regime === 'BEARISH' && m.smc_status === 'BULLISH_FVG' && (
                              <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded font-bold border border-red-500/20">
                                ⛔ Makro Engel (Sniper Harici)
                              </span>
                            )}
                            {btcRegime?.regime === 'BULLISH' && m.smc_status === 'BULLISH_FVG' && (
                              <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded font-bold border border-green-500/20">
                                🎯 İzinli (Trend Yönü)
                              </span>
                            )}
                            {btcRegime?.regime === 'BULLISH' && m.smc_status === 'BEARISH_FVG' && (
                              <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded font-bold border border-red-500/20">
                                ⛔ Makro Engel
                              </span>
                            )}
                          </div>
                        ) : <span className="text-gray-500">BEKLENIYOR</span>}
                      </td>
                      <td className="px-6 py-5 text-right font-medium text-xs">
                        {m?.fvg_depth !== undefined ? (
                          <span className={m.fvg_depth >= 0.20 ? 'text-[#0ECB81]' : 'text-[#F6465D]'}>
                            %{m.fvg_depth.toFixed(2)}
                          </span>
                        ) : <span className="text-gray-500">-</span>}
                      </td>
                      <td className={`px-6 py-5 text-center ${selectedSymbol ? 'hidden' : ''}`}>
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

      {/* Embedded TradingView Chart (Right Side) */}
      {selectedSymbol && (
        <div className="h-[500px] xl:h-auto xl:w-[65%] bg-[#0B0E11] rounded-xl border border-[#1f2937] shrink-0 overflow-hidden relative shadow-lg flex flex-col animate-in slide-in-from-right-4 fade-in duration-300">
          <div className="bg-[#121822] text-xs font-bold px-4 py-3 text-gray-300 border-b border-[#1f2937] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#0ECB81] animate-pulse" />
              <span className="tracking-wider">{selectedSymbol.toUpperCase()} / USDT</span>
            </div>
            <button 
              onClick={() => setSelectedSymbol(null)}
              className="text-gray-500 hover:text-white transition-colors flex items-center gap-1"
            >
              Kapat X
            </button>
          </div>
          <div className="flex-1 w-full relative">
            <iframe
              id="tradingview_chart"
              src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BINANCE%3A${selectedSymbol.toUpperCase()}&interval=1&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides=%7B%7D`}
              style={{ width: '100%', height: '100%', margin: '0 !important', padding: '0 !important', position: 'absolute', top: 0, left: 0 }}
              frameBorder="0"
              allowTransparency="true"
              scrolling="no"
              allowFullScreen
            ></iframe>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
