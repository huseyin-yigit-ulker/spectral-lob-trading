import React, { useState, useEffect, useMemo } from 'react';
import { 
  Activity, 
  TerminalSquare, 
  Wifi, 
  Info, 
  X, 
  Maximize2, 
  Minimize2, 
  Columns, 
  Layout, 
  Search, 
  SlidersHorizontal, 
  ExternalLink,
  BookOpen,
  ArrowUpRight,
  ArrowDownRight,
  Zap,
  TrendingDown,
  ShieldCheck
} from 'lucide-react';
import { useLive } from '../context/LiveContext';
import Tooltip from '../components/Tooltip';

export default function LiveTerminal() {
  const { symbols, metrics, wsStatus, activePeriodString, btcRegime } = useLive();
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  
  // Görünüm Seçenekleri: 'modal' (varsayılan geniş rahat), 'bottom' (altta grafik), 'split' (yan yana)
  const [chartMode, setChartMode] = useState('modal');
  const [chartInterval, setChartInterval] = useState('1'); // 1, 5, 15, 60
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('default'); // 'default', 'obi', 'cvd', 'fvg'
  const [showRulesModal, setShowRulesModal] = useState(false);
  const [isChartMaximized, setIsChartMaximized] = useState(false);

  // Sembol listesi boşalırsa seçimi temizle
  useEffect(() => {
    if (symbols.length === 0) {
      setSelectedSymbol(null);
    }
  }, [symbols]);

  // ESC tuşu ile modal/grafik kapatma desteği
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (showRulesModal) setShowRulesModal(false);
        else if (selectedSymbol && chartMode === 'modal') setSelectedSymbol(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showRulesModal, selectedSymbol, chartMode]);

  // Arama ve sıralama filtresi
  const filteredSymbols = useMemo(() => {
    let list = [...symbols];
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase().trim();
      list = list.filter(s => s.toLowerCase().includes(q));
    }

    if (sortBy === 'obi') {
      list.sort((a, b) => Math.abs((metrics[b]?.obi || 0)) - Math.abs((metrics[a]?.obi || 0)));
    } else if (sortBy === 'cvd') {
      list.sort((a, b) => Math.abs((metrics[b]?.cvd || 0)) - Math.abs((metrics[a]?.cvd || 0)));
    } else if (sortBy === 'fvg') {
      list.sort((a, b) => (metrics[b]?.fvg_depth || 0) - (metrics[a]?.fvg_depth || 0));
    }

    return list;
  }, [symbols, metrics, searchTerm, sortBy]);

  // CVD Formatlama (K/M)
  const formatCVD = (val) => {
    if (val === undefined || val === 0) return '0.00';
    const absVal = Math.abs(val);
    let formatted = absVal.toFixed(0);
    if (absVal >= 1000000) formatted = (absVal / 1000000).toFixed(2) + 'M';
    else if (absVal >= 1000) formatted = (absVal / 1000).toFixed(1) + 'K';
    return (val > 0 ? '+' : val < 0 ? '-' : '') + '$' + formatted;
  };

  // Mini OBI İlerleme / Dengesizlik Çubuğu (-1.0 ile +1.0 arası)
  const renderOBIMeter = (obi) => {
    if (obi === undefined || isNaN(obi)) return null;
    const clamped = Math.max(-1, Math.min(1, obi));
    const isBull = clamped > 0;
    const widthPct = Math.min(100, Math.abs(clamped) * 100);

    return (
      <div className="w-24 bg-[#1f2937]/80 h-1.5 rounded-full overflow-hidden flex relative mt-1 border border-white/5">
        {/* Merkez Referans Çizgisi (0.0) */}
        <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-gray-500 z-10" />
        {/* 0.30 ve -0.30 Eşik Çizgileri */}
        <div className="absolute left-[35%] top-0 bottom-0 w-[1px] bg-red-400/40 z-10" />
        <div className="absolute left-[65%] top-0 bottom-0 w-[1px] bg-emerald-400/40 z-10" />

        {/* Sol (Satıcı / Negatif) Çubuğu */}
        <div className="w-1/2 flex justify-end">
          {!isBull && (
            <div 
              className={`h-full ${Math.abs(clamped) >= 0.30 ? 'bg-[#F6465D] shadow-[0_0_8px_rgba(246,70,93,0.8)]' : 'bg-red-500/60'}`}
              style={{ width: `${widthPct}%` }}
            />
          )}
        </div>

        {/* Sağ (Alıcı / Pozitif) Çubuğu */}
        <div className="w-1/2 flex justify-start">
          {isBull && (
            <div 
              className={`h-full ${clamped >= 0.30 ? 'bg-[#0ECB81] shadow-[0_0_8px_rgba(14,203,129,0.8)]' : 'bg-emerald-500/60'}`}
              style={{ width: `${widthPct}%` }}
            />
          )}
        </div>
      </div>
    );
  };

  // Seçili coinin anlık metrikleri (grafik başlığında göstermek için)
  const selectedMetrics = selectedSymbol ? (metrics[selectedSymbol] || { price: 0, obi: 0, cvd: 0 }) : null;

  return (
    <div className="space-y-3.5 h-full flex flex-col font-sans">
      
      {/* 1. ÜST BAŞLIK & KONTROL ÇUBUĞU */}
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-center gap-3 border-b border-[#1f2937] pb-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#F0B90B]/10 border border-[#F0B90B]/30 flex items-center justify-center shrink-0">
            <TerminalSquare className="text-[#F0B90B]" size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-gray-100 tracking-tight">Live Terminal</h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-[#F0B90B]/20 text-[#F0B90B] border border-[#F0B90B]/30">
                V5.2 PRO
              </span>
              <span className="text-xs text-gray-400 font-medium hidden sm:inline">
                ({symbols.length} KABUL Onaylı Coin)
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Screener onaylı coinlerin canlı OBI, CVD ve SMC likidite boşluğu verileri</p>
          </div>
        </div>
        
        {/* Sağ Üst Kontroller & Rozetler */}
        <div className="flex flex-wrap items-center gap-2">
          
          {/* Strateji Kuralları Butonu */}
          <button
            onClick={() => setShowRulesModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1E2329] hover:bg-[#2B3139] border border-[#2B3139] hover:border-[#F0B90B]/40 rounded-lg text-xs font-bold text-gray-300 hover:text-white transition-all shadow-sm"
            title="V5.2 Strateji Parametreleri ve Giriş/Çıkış Kuralları"
          >
            <BookOpen size={14} className="text-[#F0B90B]" />
            <span>Strateji Kuralları</span>
          </button>

          {/* Grafik Açılış Modu Seçici */}
          <div className="flex items-center bg-[#121822] border border-[#1f2937] rounded-lg p-0.5 shadow-sm text-xs">
            <button
              onClick={() => setChartMode('modal')}
              className={`px-2.5 py-1 rounded-md font-bold transition-colors flex items-center gap-1 ${
                chartMode === 'modal' ? 'bg-[#F0B90B] text-black shadow' : 'text-gray-400 hover:text-gray-200'
              }`}
              title="Grafiği odak modal pencerede aç (Tablo genişliğini bozmaz)"
            >
              <Maximize2 size={12} />
              <span>Modal</span>
            </button>
            <button
              onClick={() => setChartMode('bottom')}
              className={`px-2.5 py-1 rounded-md font-bold transition-colors flex items-center gap-1 ${
                chartMode === 'bottom' ? 'bg-[#F0B90B] text-black shadow' : 'text-gray-400 hover:text-gray-200'
              }`}
              title="Grafiği tablonun altında tam genişlikte aç"
            >
              <Layout size={12} />
              <span>Altta</span>
            </button>
            <button
              onClick={() => setChartMode('split')}
              className={`px-2.5 py-1 rounded-md font-bold transition-colors flex items-center gap-1 ${
                chartMode === 'split' ? 'bg-[#F0B90B] text-black shadow' : 'text-gray-400 hover:text-gray-200'
              }`}
              title="Grafiği yan yana split görünümde aç"
            >
              <Columns size={12} />
              <span>Yan Yana</span>
            </button>
          </div>

          {/* BTC Macro Regime Pill */}
          <div className="px-3 py-1.5 bg-[#121822] border border-[#1f2937] rounded-lg shadow-sm flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              btcRegime?.regime === 'BEARISH' ? 'bg-red-500 animate-pulse' :
              btcRegime?.regime === 'BULLISH' ? 'bg-green-500 animate-pulse' :
              'bg-yellow-500'
            }`} />
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-[11px] text-gray-400 font-semibold uppercase">
                BTC: {btcRegime?.price ? `$${Number(btcRegime.price).toLocaleString('en-US', { maximumFractionDigits: 0 })}` : ''}
              </span>
              <span className={`font-black tracking-wide ${
                btcRegime?.regime === 'BEARISH' ? 'text-red-400' :
                btcRegime?.regime === 'BULLISH' ? 'text-green-400' :
                'text-yellow-400'
              }`}>
                {btcRegime?.regime === 'BEARISH' ? '🔻 SHORT' :
                 btcRegime?.regime === 'BULLISH' ? '🔺 LONG' :
                 '↔️ ÇİFT YÖN'}
              </span>
            </div>
          </div>

          {/* Active Period Badge */}
          {activePeriodString && (
            <div className="hidden sm:flex px-2.5 py-1.5 bg-[#1E2329] border border-[#2B3139] rounded-lg shadow-sm text-xs font-bold text-[#F0B90B]">
              {activePeriodString}
            </div>
          )}

          {/* WS Durumu */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#121822] border border-[#1f2937] rounded-lg shadow-sm text-xs font-bold text-gray-300">
            {wsStatus === 'CONNECTED' ? (
              <Wifi size={14} className="text-[#0ECB81] animate-pulse" />
            ) : wsStatus === 'CONNECTING' ? (
              <Wifi size={14} className="text-[#F0B90B] animate-pulse" />
            ) : (
              <Wifi size={14} className="text-[#F6465D]" />
            )}
            <span>{wsStatus}</span>
          </div>

        </div>
      </div>

      {/* 2. MAKRO FİLTRE VE V5.2 HIZLI KURAL ŞERİDİ */}
      <div className={`px-3.5 py-2.5 rounded-xl border flex flex-col md:flex-row md:items-center md:justify-between gap-2 text-xs shrink-0 ${
        btcRegime?.regime === 'BEARISH' ? 'bg-red-500/10 border-red-500/20 text-red-200' :
        btcRegime?.regime === 'BULLISH' ? 'bg-green-500/10 border-green-500/20 text-green-200' :
        'bg-yellow-500/10 border-yellow-500/20 text-yellow-200'
      }`}>
        <div className="flex items-center gap-2">
          <Info size={15} className="shrink-0" />
          <span>
            {btcRegime?.regime === 'BEARISH' ? (
              <span><strong>V5.2 Makro Filtresi:</strong> BTC 1H/4H düşüş trendinde. Yalnızca <strong>SHORT</strong> sinyalleri açılır. Karşı-trend LONG emirleri filtrelenir (Sniper: OBI ≥ +0.70 & FVG ≥ %0.40 hariç).</span>
            ) : btcRegime?.regime === 'BULLISH' ? (
              <span><strong>V5.2 Makro Filtresi:</strong> BTC 1H/4H yükseliş trendinde. Yalnızca <strong>LONG</strong> sinyalleri açılır. SHORT emirleri filtrelenir.</span>
            ) : (
              <span><strong>V5.2 Makro Filtresi:</strong> BTC nötr / range bölgesinde. Hem LONG hem SHORT strateji koşullarını sağlayan sinyaller açılabilir.</span>
            )}
          </span>
        </div>

        {/* Hızlı Parametre Etiketleri */}
        <div className="flex flex-wrap items-center gap-1.5 shrink-0 font-mono text-[11px]">
          <span className="px-2 py-0.5 rounded bg-black/40 border border-white/10 text-gray-300 font-semibold">
            OBI: |0.30|
          </span>
          <span className="px-2 py-0.5 rounded bg-black/40 border border-white/10 text-gray-300 font-semibold">
            CVD: &gt;0 / &lt;0
          </span>
          <span className="px-2 py-0.5 rounded bg-black/40 border border-white/10 text-gray-300 font-semibold">
            FVG: ≥%0.20
          </span>
          <span className="px-2 py-0.5 rounded bg-black/40 border border-white/10 text-emerald-400 font-semibold">
            BE: +%0.70
          </span>
          <span className="px-2 py-0.5 rounded bg-black/40 border border-white/10 text-[#F0B90B] font-semibold">
            Trail: +%1.20
          </span>
        </div>
      </div>

      {/* 3. ARAMA VE SIRALAMA ÇUBUĞU */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 shrink-0">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Sembol ara (örn: NEAR, SOL)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#121822] border border-[#1f2937] focus:border-[#F0B90B] text-gray-200 text-xs pl-8 pr-3 py-1.5 rounded-lg outline-none transition-colors"
          />
          {searchTerm && (
            <button 
              onClick={() => setSearchTerm('')} 
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              <X size={12} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-gray-500 font-medium flex items-center gap-1">
            <SlidersHorizontal size={12} /> Sırala:
          </span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-[#121822] border border-[#1f2937] text-gray-300 text-xs px-2.5 py-1.5 rounded-lg outline-none cursor-pointer hover:border-gray-600 transition-colors"
          >
            <option value="default">Varsayılan (Screener Sırası)</option>
            <option value="obi">Canlı OBI Büyüklüğüne Göre</option>
            <option value="cvd">1dk CVD Hacmine Göre</option>
            <option value="fvg">FVG Derinliğine Göre</option>
          </select>
        </div>
      </div>

      {/* 4. ANA İÇERİK ALANI (TABLO VE/VEYA SPLIT GRAFİK) */}
      <div className={`flex flex-col ${chartMode === 'split' && selectedSymbol ? 'xl:flex-row' : ''} gap-4 flex-1 min-h-[420px]`}>
        
        {/* TABLO KONTEYNERİ */}
        <div className={`bg-[#0B0E11] border border-[#1f2937] rounded-xl shadow-xl overflow-hidden flex-1 transition-all duration-300 ${
          chartMode === 'split' && selectedSymbol ? 'xl:w-[45%]' : 'w-full'
        }`}>
          <div className="overflow-x-auto h-full">
            <table className="w-full text-left text-xs whitespace-nowrap">
              <thead className="bg-[#121822] border-b border-[#1f2937] text-gray-400 font-bold tracking-wider uppercase text-[11px]">
                <tr>
                  <th className="px-3.5 py-2.5">Sembol</th>
                  <th className="px-3.5 py-2.5 text-right">Fiyat</th>
                  <th className="px-3.5 py-2.5 text-right">
                    <Tooltip text={`Canlı Emir Defteri Dengesizliği (Order Book Imbalance).\n\n• LONG Eşiği: > +0.30\n• SHORT Eşiği: < -0.30\n• V5.2 Ters OBI Çıkış: FVG bölgesinde ters yönde güçlü baskı (|OBI| ≥ 0.50) görülürse erken çıkış yapılır.`}>
                      Canlı OBI <Info size={12} className="text-[#F0B90B] inline ml-1" />
                    </Tooltip>
                  </th>
                  <th className="px-3.5 py-2.5 text-right">
                    <Tooltip text={`Kümülatif Hacim Deltası (Son 1 Dakika):\nPiyasa emirleriyle gerçekleşen anlık agresif alım/satım baskısı.\n\n• LONG Şartı: Pozitif (> 0)\n• SHORT Şartı: Negatif (< 0)`}>
                      CVD (1dk) <Info size={12} className="text-[#F0B90B] inline ml-1" />
                    </Tooltip>
                  </th>
                  <th className="px-3.5 py-2.5 text-right">
                    <Tooltip text={`Smart Money Concepts (SMC) Piyasa Yönü:\n\n• BULLISH_FVG (Alış Bölgesi)\n• BEARISH_FVG (Satış Bölgesi)\n• V5.2 Makro Filtre Uyum Durumu`}>
                      SMC / Makro Onay <Info size={12} className="text-[#F0B90B] inline ml-1" />
                    </Tooltip>
                  </th>
                  <th className="px-3.5 py-2.5 text-right">
                    <Tooltip text={`Fair Value Gap (Likidite Boşluğu) Derinliği:\n\n• V5.2 Şartı: En az %0.20 likidite marjı aranır.`}>
                      FVG Derinlik <Info size={12} className="text-[#F0B90B] inline ml-1" />
                    </Tooltip>
                  </th>
                  <th className="px-3.5 py-2.5 text-center">İşlem / Grafik</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]/50 font-mono">
                {filteredSymbols.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-14 text-center">
                      <div className="flex flex-col items-center justify-center text-gray-500">
                        <Activity size={28} className="mb-2 opacity-40 text-[#F0B90B]" />
                        <p className="text-sm font-semibold text-gray-300">İzlenecek coin bulunamadı.</p>
                        <p className="text-xs text-gray-500 mt-1">Screener yeni coinler bulduğunda burada anında belirecektir.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredSymbols.map(sym => {
                    const m = metrics[sym] || { price: 0, obi: 0, cvd: 0 };
                    const isSelected = selectedSymbol === sym;
                    const isCvdBullish = m.cvd > 0;
                    const isCvdBearish = m.cvd < 0;

                    // OBI Renk ve Stil Sınıfları
                    let obiColor = "text-gray-400";
                    let isObiSignalReady = false;
                    if (m.obi >= 0.30) {
                      obiColor = "text-[#0ECB81] font-black";
                      isObiSignalReady = true;
                    } else if (m.obi > 0) {
                      obiColor = "text-[#0ECB81]";
                    } else if (m.obi <= -0.30) {
                      obiColor = "text-[#F6465D] font-black";
                      isObiSignalReady = true;
                    } else if (m.obi < 0) {
                      obiColor = "text-[#F6465D]";
                    }

                    // Makro Filtre Uyum Durumu
                    let macroStatusTag = null;
                    if (btcRegime?.regime === 'BEARISH') {
                      if (m.smc_status === 'BEARISH_FVG') {
                        macroStatusTag = (
                          <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded font-bold border border-green-500/20">
                            🎯 Trend Uyumlu
                          </span>
                        );
                      } else if (m.smc_status === 'BULLISH_FVG') {
                        const isSniper = (m.obi >= 0.70 && (m.fvg_depth || 0) >= 0.40);
                        macroStatusTag = isSniper ? (
                          <span className="text-[10px] text-yellow-400 bg-yellow-500/20 px-1.5 py-0.5 rounded font-black border border-yellow-500/30 animate-pulse">
                            ⚡ Sniper İstisnası
                          </span>
                        ) : (
                          <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded font-bold border border-red-500/20">
                            ⛔ Makro Filtre Engeli
                          </span>
                        );
                      }
                    } else if (btcRegime?.regime === 'BULLISH') {
                      if (m.smc_status === 'BULLISH_FVG') {
                        macroStatusTag = (
                          <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded font-bold border border-green-500/20">
                            🎯 Trend Uyumlu
                          </span>
                        );
                      } else if (m.smc_status === 'BEARISH_FVG') {
                        macroStatusTag = (
                          <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded font-bold border border-red-500/20">
                            ⛔ Makro Filtre Engeli
                          </span>
                        );
                      }
                    } else {
                      // NEUTRAL
                      if (m.smc_status === 'BULLISH_FVG' || m.smc_status === 'BEARISH_FVG') {
                        macroStatusTag = (
                          <span className="text-[10px] text-yellow-400 bg-yellow-500/10 px-1.5 py-0.5 rounded font-bold border border-yellow-500/20">
                            ✅ Çift Yön Aktif
                          </span>
                        );
                      }
                    }

                    return (
                      <tr 
                        key={sym} 
                        onClick={() => setSelectedSymbol(sym)}
                        className={`transition-colors cursor-pointer ${
                          isSelected 
                            ? 'bg-[#1f2937]/80 border-l-4 border-l-[#F0B90B]' 
                            : 'hover:bg-[#151b24]'
                        }`}
                      >
                        {/* 1. Sembol */}
                        <td className="px-3.5 py-2.5 font-sans font-bold text-gray-200 uppercase">
                          <div className="flex items-center gap-2">
                            {isSelected ? (
                              <div className="w-2 h-2 rounded-full bg-[#F0B90B] animate-pulse" />
                            ) : (
                              <div className="w-1.5 h-1.5 rounded-full bg-gray-600" />
                            )}
                            <span className="tracking-wide text-xs">{sym}</span>
                          </div>
                        </td>

                        {/* 2. Fiyat */}
                        <td className="px-3.5 py-2.5 text-right text-gray-200 font-semibold text-xs">
                          {m.price ? Number(m.price).toPrecision(6) : '...'}
                        </td>

                        {/* 3. Canlı OBI */}
                        <td className="px-3.5 py-2.5 text-right">
                          <div className="flex flex-col items-end">
                            <span className={`text-xs ${obiColor} ${isObiSignalReady ? 'bg-black/30 px-1.5 py-0.5 rounded' : ''}`}>
                              {m.obi !== undefined ? (m.obi > 0 ? '+' : '') + m.obi.toFixed(3) : '...'}
                            </span>
                            {renderOBIMeter(m.obi)}
                          </div>
                        </td>

                        {/* 4. CVD (1dk) */}
                        <td className="px-3.5 py-2.5 text-right font-bold text-xs">
                          {m.cvd !== undefined ? (
                            <span className={`inline-flex items-center gap-0.5 ${
                              isCvdBullish ? 'text-[#0ECB81]' : isCvdBearish ? 'text-[#F6465D]' : 'text-gray-400'
                            }`}>
                              {isCvdBullish && <ArrowUpRight size={13} />}
                              {isCvdBearish && <ArrowDownRight size={13} />}
                              {formatCVD(m.cvd)}
                            </span>
                          ) : '...'}
                        </td>

                        {/* 5. SMC Durumu & Makro Onay */}
                        <td className="px-3.5 py-2.5 text-right">
                          {m?.smc_status ? (
                            <div className="flex flex-col items-end gap-1">
                              <span className={`text-[11px] font-bold ${
                                m.smc_status === 'BULLISH_FVG' ? 'text-[#0ECB81]' :
                                m.smc_status === 'BEARISH_FVG' ? 'text-[#F6465D]' :
                                'text-gray-400'
                              }`}>
                                {m.smc_status}
                              </span>
                              {macroStatusTag}
                            </div>
                          ) : (
                            <span className="text-gray-500 text-[11px]">BEKLENİYOR</span>
                          )}
                        </td>

                        {/* 6. FVG Derinlik */}
                        <td className="px-3.5 py-2.5 text-right text-xs font-semibold">
                          {m?.fvg_depth !== undefined ? (
                            <span className={m.fvg_depth >= 0.20 ? 'text-[#0ECB81]' : 'text-gray-400'}>
                              %{m.fvg_depth.toFixed(2)}
                            </span>
                          ) : (
                            <span className="text-gray-500">-</span>
                          )}
                        </td>

                        {/* 7. Grafik Aç Butonu */}
                        <td className="px-3.5 py-2.5 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedSymbol(sym);
                            }}
                            className={`px-2 py-1 rounded text-[11px] font-bold transition-all flex items-center gap-1 mx-auto ${
                              isSelected
                                ? 'bg-[#F0B90B] text-black shadow-md'
                                : 'bg-[#1E2329] hover:bg-[#2B3139] text-gray-300 hover:text-white border border-[#2B3139]'
                            }`}
                          >
                            <span>Grafik</span>
                            <ArrowUpRight size={12} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* YAN YANA (SPLIT) GÖRÜNÜMDE GRAFİK PANELİ */}
        {chartMode === 'split' && selectedSymbol && (
          <div className="h-[480px] xl:h-auto xl:w-[55%] bg-[#0B0E11] rounded-xl border border-[#1f2937] shrink-0 overflow-hidden relative shadow-2xl flex flex-col animate-in fade-in duration-200">
            {/* Header */}
            <div className="bg-[#121822] text-xs font-bold px-3.5 py-2 text-gray-300 border-b border-[#1f2937] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#0ECB81] animate-pulse" />
                <span className="font-black text-gray-100">{selectedSymbol.toUpperCase()} / USDT</span>
                <span className="text-gray-400 font-mono">
                  {selectedMetrics?.price ? `$${Number(selectedMetrics.price).toPrecision(6)}` : ''}
                </span>
              </div>
              
              <div className="flex items-center gap-1.5">
                {/* Periyot Seçici */}
                {['1', '5', '15', '60'].map(iv => (
                  <button
                    key={iv}
                    onClick={() => setChartInterval(iv)}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      chartInterval === iv ? 'bg-[#F0B90B] text-black' : 'text-gray-400 hover:text-white bg-[#1E2329]'
                    }`}
                  >
                    {iv === '60' ? '1s' : `${iv}d`}
                  </button>
                ))}
                
                <button 
                  onClick={() => setSelectedSymbol(null)}
                  className="ml-2 text-gray-400 hover:text-white p-1 rounded hover:bg-[#1E2329]"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* TradingView iframe */}
            <div className="flex-1 w-full relative">
              <iframe
                id="tradingview_chart_split"
                key={`${selectedSymbol}-${chartInterval}`}
                src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BINANCE%3A${selectedSymbol.toUpperCase()}&interval=${chartInterval}&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides=%7B%7D`}
                style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
                frameBorder="0"
                allowTransparency="true"
                scrolling="no"
                allowFullScreen
              />
            </div>
          </div>
        )}

      </div>

      {/* 5. ALTA EKLENEN GRAFİK PANELİ (chartMode === 'bottom') */}
      {chartMode === 'bottom' && selectedSymbol && (
        <div className="h-[460px] bg-[#0B0E11] rounded-xl border border-[#1f2937] shrink-0 overflow-hidden relative shadow-2xl flex flex-col animate-in fade-in duration-200">
          <div className="bg-[#121822] text-xs font-bold px-4 py-2.5 text-gray-300 border-b border-[#1f2937] flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#0ECB81] animate-pulse" />
                <span className="font-black text-gray-100 text-sm">{selectedSymbol.toUpperCase()} / USDT</span>
                <span className="text-[#F0B90B] font-mono font-bold">
                  {selectedMetrics?.price ? `$${Number(selectedMetrics.price).toPrecision(6)}` : ''}
                </span>
              </div>
              <div className="hidden sm:flex items-center gap-2 text-xs font-mono">
                <span className="text-gray-400">OBI: <strong className="text-white">{selectedMetrics?.obi?.toFixed(3)}</strong></span>
                <span className="text-gray-400">CVD: <strong className="text-white">{formatCVD(selectedMetrics?.cvd)}</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center bg-[#1E2329] p-0.5 rounded-lg border border-[#2B3139]">
                {['1', '5', '15', '60'].map(iv => (
                  <button
                    key={iv}
                    onClick={() => setChartInterval(iv)}
                    className={`px-2 py-0.5 rounded text-xs font-bold ${
                      chartInterval === iv ? 'bg-[#F0B90B] text-black shadow' : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {iv === '60' ? '1s' : `${iv}d`}
                  </button>
                ))}
              </div>

              <a
                href={`https://www.binance.com/tr/futures/${selectedSymbol.toUpperCase()}`}
                target="_blank"
                rel="noreferrer"
                className="p-1 text-gray-400 hover:text-white hover:bg-[#1E2329] rounded"
                title="Binance Futures'da Aç"
              >
                <ExternalLink size={14} />
              </a>

              <button 
                onClick={() => setSelectedSymbol(null)}
                className="text-gray-400 hover:text-white p-1 rounded hover:bg-[#1E2329]"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          <div className="flex-1 w-full relative">
            <iframe
              id="tradingview_chart_bottom"
              key={`${selectedSymbol}-${chartInterval}`}
              src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BINANCE%3A${selectedSymbol.toUpperCase()}&interval=${chartInterval}&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides=%7B%7D`}
              style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
              frameBorder="0"
              allowTransparency="true"
              scrolling="no"
              allowFullScreen
            />
          </div>
        </div>
      )}

      {/* 6. MODAL GRAFİK PENCERESİ (chartMode === 'modal') */}
      {chartMode === 'modal' && selectedSymbol && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
          <div className={`bg-[#0B0E11] border border-[#1f2937] rounded-2xl shadow-2xl overflow-hidden flex flex-col transition-all ${
            isChartMaximized ? 'w-full h-full' : 'w-full max-w-6xl h-[88vh]'
          }`}>
            
            {/* Modal Üst Başlık Çubuğu */}
            <div className="bg-[#121822] px-4 py-3 border-b border-[#1f2937] flex flex-wrap items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[#0ECB81] animate-pulse" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base font-black text-gray-100">{selectedSymbol.toUpperCase()} / USDT</span>
                    <span className="text-xs px-2 py-0.5 rounded font-black bg-[#F0B90B]/20 text-[#F0B90B] border border-[#F0B90B]/30">
                      BINANCE FUTURES
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs font-mono mt-0.5">
                    <span className="text-gray-400">
                      Anlık Fiyat: <strong className="text-white">${selectedMetrics?.price ? Number(selectedMetrics.price).toPrecision(6) : '...'}</strong>
                    </span>
                    <span className="text-gray-400">
                      OBI: <strong className={selectedMetrics?.obi >= 0.3 ? 'text-green-400' : selectedMetrics?.obi <= -0.3 ? 'text-red-400' : 'text-white'}>
                        {selectedMetrics?.obi?.toFixed(3)}
                      </strong>
                    </span>
                    <span className="text-gray-400">
                      CVD: <strong className="text-white">{formatCVD(selectedMetrics?.cvd)}</strong>
                    </span>
                  </div>
                </div>
              </div>

              {/* Kontroller: Periyot + Tam Ekran + Binance Linki + Kapat */}
              <div className="flex items-center gap-2">
                <div className="flex items-center bg-[#1E2329] p-0.5 rounded-lg border border-[#2B3139]">
                  {['1', '5', '15', '60'].map(iv => (
                    <button
                      key={iv}
                      onClick={() => setChartInterval(iv)}
                      className={`px-2.5 py-1 rounded text-xs font-bold transition-colors ${
                        chartInterval === iv ? 'bg-[#F0B90B] text-black shadow' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      {iv === '60' ? '1s' : `${iv}d`}
                    </button>
                  ))}
                </div>

                <a
                  href={`https://www.binance.com/tr/futures/${selectedSymbol.toUpperCase()}`}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-[#1E2329] rounded-lg transition-colors"
                  title="Binance'de Aç"
                >
                  <ExternalLink size={16} />
                </a>

                <button
                  onClick={() => setIsChartMaximized(!isChartMaximized)}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-[#1E2329] rounded-lg transition-colors"
                  title={isChartMaximized ? 'Küçült' : 'Tam Ekran'}
                >
                  {isChartMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>

                <button
                  onClick={() => setSelectedSymbol(null)}
                  className="p-1.5 text-gray-400 hover:text-white bg-[#1E2329] hover:bg-red-500/20 hover:text-red-300 rounded-lg transition-colors"
                  title="Kapat (ESC)"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* TradingView Grafiği */}
            <div className="flex-1 w-full relative bg-[#0B0E11]">
              <iframe
                id="tradingview_chart_modal"
                key={`${selectedSymbol}-${chartInterval}`}
                src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BINANCE%3A${selectedSymbol.toUpperCase()}&interval=${chartInterval}&hidesidetoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&withdateranges=1&showpopupbutton=1&studies_overrides=%7B%7D`}
                style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
                frameBorder="0"
                allowTransparency="true"
                scrolling="no"
                allowFullScreen
              />
            </div>

          </div>
        </div>
      )}

      {/* 7. V5.2 STRATEJİ VE RİSK YÖNETİMİ KURALLARI MODALI */}
      {showRulesModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-[#0B0E11] border border-[#1f2937] rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            
            <button 
              onClick={() => setShowRulesModal(false)}
              className="absolute right-4 top-4 text-gray-400 hover:text-white p-1 rounded-lg hover:bg-[#1E2329]"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3 border-b border-[#1f2937] pb-4 mb-4">
              <div className="w-10 h-10 rounded-xl bg-[#F0B90B]/10 border border-[#F0B90B]/30 flex items-center justify-center text-[#F0B90B]">
                <ShieldCheck size={22} />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">QUANT V5.2 Strateji Parametreleri & Kurallar</h3>
                <p className="text-xs text-gray-400">Canlı botun işlem açma, filtreleme ve pozisyon kapatma mantığı</p>
              </div>
            </div>

            <div className="space-y-4 text-xs text-gray-300">
              
              {/* Kural 1: Makro Filtre */}
              <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3.5 space-y-1.5">
                <div className="flex items-center gap-2 font-black text-sm text-[#F0B90B]">
                  <TrendingDown size={16} /> 1. Bitcoin Makro Trend Filtresi (Gatekeeper)
                </div>
                <p className="text-gray-400 leading-relaxed">
                  Bitcoin 1H & 4H periyotlarında EMA 50 / EMA 200 altına düştüğünde sistem <strong>DÜŞÜŞ (BEARISH)</strong> rejimine geçer ve altcoin LONG sinyallerini otomatik filtreler (yalnızca SHORT açılır).
                </p>
                <div className="bg-black/40 p-2 rounded border border-white/5 text-[11px] font-mono text-yellow-300">
                  ⚡ <strong>Sniper İstisnası:</strong> Karşıt yönde aşırı kurumsal emir girişi olursa (<code>OBI ≥ +0.70</code> ve <code>FVG Derinliği ≥ %0.40</code>), BTC trendine rağmen bağımsız scalp pozisyon açılabilir.
                </div>
              </div>

              {/* Kural 2: Giriş Onayları */}
              <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3.5 space-y-1.5">
                <div className="flex items-center gap-2 font-black text-sm text-[#0ECB81]">
                  <Zap size={16} /> 2. Otomatik Giriş Şartları
                </div>
                <ul className="list-disc list-inside space-y-1 text-gray-400 ml-1">
                  <li><strong>Canlı OBI Eşiği:</strong> LONG için <code>&gt; +0.30</code> | SHORT için <code>&lt; -0.30</code></li>
                  <li><strong>CVD (1dk) Eşiği:</strong> LONG için <code>&gt; 0 (Pozitif)</code> | SHORT için <code>&lt; 0 (Negatif)</code></li>
                  <li><strong>SMC Bölgesi:</strong> LONG için <code>BULLISH_FVG</code> | SHORT için <code>BEARISH_FVG</code></li>
                  <li><strong>FVG Derinliği:</strong> En az <code>%0.20</code> likidite marjı aranır.</li>
                </ul>
              </div>

              {/* Kural 3: Pozisyon Yönetimi ve Çıkışlar */}
              <div className="bg-[#121822] border border-[#1f2937] rounded-xl p-3.5 space-y-1.5">
                <div className="flex items-center gap-2 font-black text-sm text-cyan-400">
                  <Activity size={16} /> 3. V5.2 Çıkış ve Risk Yönetimi
                </div>
                <ul className="list-disc list-inside space-y-1 text-gray-400 ml-1">
                  <li><strong>Mum Kapanış Teyitli SL:</strong> İğne (wick) gürültülerine karşı 1m mum kapanışıyla teyit edilen yapısal SL.</li>
                  <li><strong>Hard Acil Stop:</strong> Fiyat aleyhe <code>%1.00</code> giderse mum kapanışı beklenmeksizin anında Hard Stop.</li>
                  <li><strong>Break-Even (Başa Baş):</strong> PnL <code>+%0.70</code> seviyesini gördüğünde SL seviyesi giriş fiyatına çekilir (Risk Sıfırlama).</li>
                  <li><strong>Trailing Stop (İzleyen Kâr):</strong> PnL <code>+%1.20</code> seviyesine ulaştığında kâr kilitleme devreye girer.</li>
                  <li><strong>Ters OBI Erken Çıkış:</strong> FVG hedefinde ters yönde kurumsal emir yığılması (<code>Ters OBI ≥ 0.50</code>) oluşursa kâr korunarak erken çıkılır.</li>
                </ul>
              </div>

            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setShowRulesModal(false)}
                className="px-4 py-2 bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black font-black text-xs rounded-lg transition-colors"
              >
                Anladım, Kapat
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
