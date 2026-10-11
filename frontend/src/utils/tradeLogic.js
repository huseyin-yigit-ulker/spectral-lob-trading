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

export function reconstructTrades(rawLogs) {
  // rawLogs'u eskiden yeniye dogru sirala
  const sortedLogs = [...rawLogs].sort((a, b) => parseUtcDate(a.zaman) - parseUtcDate(b.zaman));
  
  const openPositions = {};
  const closedTrades = [];

  sortedLogs.forEach(log => {
    const sym = log.sembol;
    const isEntry = log.sinyal.includes('AL') || log.sinyal.includes('SAT');
    const isExit = log.sinyal.includes('BEKLE');

    if (isEntry) {
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
        fvg_depth: Number(log.fvg_depth || 0),
        context: log.context || 'NEUTRAL',
        sinyal: log.sinyal,
        status: 'OPEN'
      };
    } else if (isExit && openPositions[sym]) {
      const pos = openPositions[sym];
      pos.cikis_zaman = log.zaman;
      pos.cikis_fiyat = Number(log.fiyat);
      pos.cikis_obi = Number(log.obi || 0);
      pos.cikis_cvd = Number(log.cvd || 0);
      pos.status = 'CLOSED';
      
      const diff = pos.yön === 'LONG' ? (pos.cikis_fiyat - pos.giris_fiyat) : (pos.giris_fiyat - pos.cikis_fiyat);
      pos.fiyat_fark = diff;
      pos.pnl_yuzde = (diff / pos.giris_fiyat) * 100;
      
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
    return pos;
  });
  
  // Hepsini birlestir, en yeniden eskiye sirala (UI gosterimi icin)
  const allTrades = [...activeTrades, ...closedTrades].sort((a, b) => parseUtcDate(b.giris_zaman) - parseUtcDate(a.giris_zaman));

  // Istatistikler
  let totalPnl = 0;
  let wins = 0;
  let losses = 0;

  closedTrades.forEach(t => {
    totalPnl += t.pnl_yuzde;
    if (t.pnl_yuzde > 0) wins++;
    else if (t.pnl_yuzde < 0) losses++;
  });

  const totalClosed = wins + losses;
  const winRate = totalClosed > 0 ? (wins / totalClosed) * 100 : 0;

  return {
    allTrades,
    activeTrades,
    closedTrades,
    stats: {
      totalPnl,
      winRate,
      totalClosed,
      wins,
      losses,
      activeCount: activeTrades.length
    }
  };
}

