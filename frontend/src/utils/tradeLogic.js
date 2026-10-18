export function parseUtcDate(dateStr) {
  if (!dateStr) return new Date();
  if (dateStr instanceof Date) return dateStr;
  let s = String(dateStr).trim();
  if (s.endsWith('Z') || /[+-]\d{2}(:\d{2})?$/.test(s)) {
    return new Date(s);
  }
  return new Date(s.replace(' ', 'T') + 'Z');
}

export function formatUtcDateTime(dateStr, includeSeconds = true) {
  if (!dateStr) return '-';
  const d = parseUtcDate(dateStr);
  if (isNaN(d.getTime())) return '-';
  const day = String(d.getUTCDate()).padStart(2, '0');
  const month = String(d.getUTCMonth() + 1).padStart(2, '0');
  const year = d.getUTCFullYear();
  const hours = String(d.getUTCHours()).padStart(2, '0');
  const mins = String(d.getUTCMinutes()).padStart(2, '0');
  const secs = String(d.getUTCSeconds()).padStart(2, '0');
  return includeSeconds 
    ? `${day}.${month}.${year} ${hours}:${mins}:${secs} UTC`
    : `${day}.${month}.${year} ${hours}:${mins} UTC`;
}

export function formatUtcTime(dateStr, includeSeconds = true) {
  if (!dateStr) return '-';
  const d = parseUtcDate(dateStr);
  if (isNaN(d.getTime())) return '-';
  const hours = String(d.getUTCHours()).padStart(2, '0');
  const mins = String(d.getUTCMinutes()).padStart(2, '0');
  const secs = String(d.getUTCSeconds()).padStart(2, '0');
  return includeSeconds ? `${hours}:${mins}:${secs} UTC` : `${hours}:${mins} UTC`;
}

export function formatSmartPrice(price) {
  if (price === undefined || price === null || isNaN(price)) return '-';
  const num = Number(price);
  if (num === 0) return '0.00';
  if (num < 0.0001) return num.toFixed(7);
  if (num < 0.01) return num.toFixed(6);
  if (num < 1) return num.toFixed(5);
  if (num < 10) return num.toFixed(4);
  if (num < 1000) return num.toFixed(2);
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function reconstructTrades(rawLogs, version = 'v5_5') {
  // rawLogs'u eskiden yeniye dogru sirala
  const sortedLogs = [...rawLogs].sort((a, b) => parseUtcDate(a.zaman) - parseUtcDate(b.zaman));
  
  const openPositions = {};
  const closedTrades = [];

  sortedLogs.forEach(log => {
    const sym = log.sembol;
    const isEntry = log.sinyal.includes('AL') || log.sinyal.includes('SAT');
    const isExit = log.sinyal.includes('BEKLE');

    if (isEntry) {
      const isSniper = log.entry_reason ? log.entry_reason.toLowerCase().includes('sniper') : (Math.abs(Number(log.obi || 0)) >= 0.70 && Number(log.fvg_depth || 0) >= 0.40);
      const btcRegime = log.btc_regime || (isSniper ? 'BEARISH' : 'NEUTRAL');
      const entryReason = log.entry_reason || (isSniper 
        ? `Sniper İstisnası: Altcoin BTC'den Pozitif Ayrıştı (OBI: ${Number(log.obi || 0) > 0 ? '+' : ''}${Number(log.obi || 0).toFixed(2)})` 
        : `BTC Trend Uyumlu (${btcRegime})`);
      
      const fvgDepth = Number(log.fvg_depth || 0);
      const isExcessiveFvg = fvgDepth > 1.50;
      const isTooSmallFvg = fvgDepth > 0 && fvgDepth < 0.15;
      const isNeutralBearLong = log.sinyal.includes('AL') && (!isSniper) && (btcRegime === 'NEUTRAL' || btcRegime === 'BEARISH' || btcRegime === 'UNKNOWN');

      let isFiltered = false;
      let filterReason = '';

      if (version === 'v5_5') {
        if (isExcessiveFvg) {
          isFiltered = true;
          filterReason = 'FVG > %1.50 (Manipülatif Aşırı FVG)';
        } else if (isTooSmallFvg) {
          isFiltered = true;
          filterReason = 'FVG < %0.15 (Yetersiz Likidite Marjı)';
        } else if (isNeutralBearLong) {
          isFiltered = true;
          filterReason = '4H Ayı Trendinde Altcoin LONG Bloke Edildi';
        }
      } else if (version === 'v5_4') {
        if (isExcessiveFvg) {
          isFiltered = true;
          filterReason = 'FVG > %1.50 (Manipülatif Aşırı FVG)';
        } else if (isNeutralBearLong) {
          isFiltered = true;
          filterReason = '4H Ayı Trendinde Altcoin LONG Bloke Edildi';
        }
      }

      openPositions[sym] = {
        id: log.id,
        sembol: sym,
        yön: log.sinyal.includes('AL') ? 'LONG' : 'SHORT',
        giris_zaman: log.zaman,
        giris_fiyat: Number(log.fiyat),
        fvg_top: Number(log.fvg_top || 0),
        fvg_bottom: Number(log.fvg_bottom || 0),
        obi: Number(log.obi || 0),
        cvd: Number(log.cvd || 0),
        fvg_depth: fvgDepth,
        context: log.context || 'NEUTRAL',
        sinyal: log.sinyal,
        rlr: Number(log.rlr || 1.0),
        bsi: Number(log.bsi || 0),
        clean_obi: Number(log.clean_obi || 0),
        btc_regime: btcRegime,
        entry_reason: entryReason,
        is_sniper: isSniper,
        is_filtered: isFiltered,
        filter_reason: filterReason,
        version: version === 'v5_5' ? 'V5.5' : version === 'v5_4' ? 'V5.4' : 'V5.3',
        status: 'OPEN'
      };
    } else if (isExit && openPositions[sym]) {
      const pos = openPositions[sym];
      pos.cikis_zaman = log.zaman;
      pos.cikis_fiyat = Number(log.fiyat);
      pos.cikis_obi = Number(log.obi || 0);
      pos.cikis_cvd = Number(log.cvd || 0);
      pos.status = 'CLOSED';
      
      let diff = pos.yön === 'LONG' ? (pos.cikis_fiyat - pos.giris_fiyat) : (pos.giris_fiyat - pos.cikis_fiyat);
      let pnlPct = (diff / pos.giris_fiyat) * 100;

      // Filtreleme ve Hard Stop Kontrolleri
      const isExcessiveFvg = pos.fvg_depth > 1.50;
      const isTooSmallFvg = pos.fvg_depth > 0 && pos.fvg_depth < 0.15;
      const isNeutralBearLong = pos.yön === 'LONG' && (!pos.is_sniper) && (pos.btc_regime === 'NEUTRAL' || pos.btc_regime === 'BEARISH' || pos.btc_regime === 'UNKNOWN');

      if (version === 'v5_5') {
        if (isExcessiveFvg) {
          pos.is_filtered = true;
          pos.filter_reason = 'FVG > %1.50 (Manipülatif Aşırı FVG)';
        } else if (isTooSmallFvg) {
          pos.is_filtered = true;
          pos.filter_reason = 'FVG < %0.15 (Yetersiz Likidite Marjı)';
        } else if (isNeutralBearLong) {
          pos.is_filtered = true;
          pos.filter_reason = '4H Ayı Trendinde Altcoin LONG Bloke Edildi';
        } else {
          pos.is_filtered = false;
          if (pnlPct < -0.70) {
            pnlPct = -0.70;
            pos.cikis_fiyat = pos.yön === 'LONG' ? pos.giris_fiyat * 0.9930 : pos.giris_fiyat * 1.0070;
            pos.hard_sl_triggered = true;
            diff = pos.yön === 'LONG' ? (pos.cikis_fiyat - pos.giris_fiyat) : (pos.giris_fiyat - pos.cikis_fiyat);
          }
        }
        pos.version = 'V5.5';
      } else if (version === 'v5_4') {
        if (isExcessiveFvg) {
          pos.is_filtered = true;
          pos.filter_reason = 'FVG > %1.50 (Manipülatif Aşırı FVG)';
        } else if (isNeutralBearLong) {
          pos.is_filtered = true;
          pos.filter_reason = '4H Ayı Trendinde Altcoin LONG Bloke Edildi';
        } else {
          pos.is_filtered = false;
          if (pnlPct < -0.70) {
            pnlPct = -0.70;
            pos.cikis_fiyat = pos.yön === 'LONG' ? pos.giris_fiyat * 0.9930 : pos.giris_fiyat * 1.0070;
            pos.hard_sl_triggered = true;
            diff = pos.yön === 'LONG' ? (pos.cikis_fiyat - pos.giris_fiyat) : (pos.giris_fiyat - pos.cikis_fiyat);
          }
        }
        pos.version = 'V5.4';
      } else {
        pos.is_filtered = false;
        pos.version = 'V5.3';
      }

      // Komisyon Hesabı: Limit (Maker) Emir için Giriş %0.02 + Çıkış %0.02 = %0.04
      const MAKER_FEE_PCT = 0.04;
      const brutPnl = pnlPct;
      const netPnl = Number((brutPnl - MAKER_FEE_PCT).toFixed(3));

      pos.fiyat_fark = diff;
      pos.brut_pnl = brutPnl;
      pos.net_pnl = netPnl;
      pos.komisyon_pct = MAKER_FEE_PCT;
      pos.pnl_yuzde = netPnl; // Birincil pnl net kârdır
      pos.pnl_pct = netPnl;
      pos.win = netPnl > 0;
      pos.brut_win = brutPnl > 0;
      pos.tip = pos.yön;
      pos.entry_price = pos.giris_fiyat;
      pos.exit_price = pos.cikis_fiyat;
      pos.entry_time = pos.giris_zaman;
      pos.exit_time = pos.cikis_zaman;
      
      // Süre hesabi
      const ms = parseUtcDate(pos.cikis_zaman).getTime() - parseUtcDate(pos.giris_zaman).getTime();
      pos.sure_ms = ms;
      pos.sure_dk = Math.max(0, Math.floor(ms / 60000));
      if (ms < 60000) {
        pos.sure_str = `${Math.max(1, Math.floor(ms / 1000))} sn`;
      } else if (pos.sure_dk < 60) {
        pos.sure_str = `${pos.sure_dk} dk`;
      } else {
        const h = Math.floor(pos.sure_dk / 60);
        const m = pos.sure_dk % 60;
        pos.sure_str = `${h}s ${m}d`;
      }
      
      closedTrades.push(pos);
      delete openPositions[sym];
    }
  });

  const activeTrades = Object.values(openPositions).map(pos => {
    const ms = Date.now() - parseUtcDate(pos.giris_zaman).getTime();
    pos.sure_ms = ms;
    pos.sure_dk = Math.max(0, Math.floor(ms / 60000));
    pos.sure_str = pos.sure_dk < 60 ? `${pos.sure_dk} dk` : `${Math.floor(pos.sure_dk / 60)}s ${pos.sure_dk % 60}d`;
    pos.tip = pos.yön;
    pos.entry_price = pos.giris_fiyat;
    pos.entry_time = pos.giris_zaman;
    return pos;
  });
  
  // Hepsini birlestir, en yeniden eskiye sirala (UI gosterimi icin)
  const allTrades = [...activeTrades, ...closedTrades].sort((a, b) => parseUtcDate(b.giris_zaman) - parseUtcDate(a.giris_zaman));

  // Istatistikler (Filtrelenmemis gercek islemler uzerinden)
  let totalNetPnl = 0;
  let totalBrutPnl = 0;
  let netWins = 0;
  let brutWins = 0;
  let netLosses = 0;
  let brutLosses = 0;
  let filteredCount = 0;
  let preventedLossPnl = 0;
  let validCount = 0;

  closedTrades.forEach(t => {
    if (!t.is_filtered) {
      validCount++;
      const netVal = t.net_pnl !== undefined ? t.net_pnl : (t.pnl_yuzde - 0.04);
      const brutVal = t.brut_pnl !== undefined ? t.brut_pnl : t.pnl_yuzde;
      totalNetPnl += netVal;
      totalBrutPnl += brutVal;
      if (netVal > 0) netWins++;
      else if (netVal < 0) netLosses++;
      if (brutVal > 0) brutWins++;
      else if (brutVal < 0) brutLosses++;
    } else {
      filteredCount++;
      if (t.pnl_yuzde < 0) {
        preventedLossPnl += Math.abs(t.pnl_yuzde);
      }
    }
  });

  const totalClosed = validCount;
  const netWinRate = totalClosed > 0 ? (netWins / totalClosed) * 100 : 0;
  const brutWinRate = totalClosed > 0 ? (brutWins / totalClosed) * 100 : 0;
  const totalCommission = totalClosed * 0.04;

  return {
    allTrades,
    activeTrades,
    closedTrades,
    stats: {
      totalPnl: totalNetPnl,
      totalNetPnl,
      totalBrutPnl,
      totalCommission,
      winRate: netWinRate,
      netWinRate,
      brutWinRate,
      totalClosed,
      wins: netWins,
      losses: netLosses,
      netWins,
      netLosses,
      brutWins,
      brutLosses,
      activeCount: activeTrades.length,
      filteredCount,
      preventedLossPnl
    }
  };
}

