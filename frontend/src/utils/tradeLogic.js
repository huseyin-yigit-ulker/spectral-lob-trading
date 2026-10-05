export function reconstructTrades(rawLogs) {
  // rawLogs'u eskiden yeniye dogru sirala
  const sortedLogs = [...rawLogs].sort((a, b) => new Date(a.zaman) - new Date(b.zaman));
  
  const openPositions = {};
  const closedTrades = [];

  sortedLogs.forEach(log => {
    const sym = log.sembol;
    const isEntry = log.sinyal.includes('AL') || log.sinyal.includes('SAT');
    const isExit = log.sinyal.includes('BEKLE');

    if (isEntry) {
      // Eger onceden acik kalmis bir islem varsa onu iptal say veya kapat
      if (openPositions[sym]) {
        // Gormezden gelebiliriz veya timeout ile kapatabiliriz, basitlik icin eziyoruz
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
        fvg_depth: Number(log.fvg_depth || 0),
        context: log.context,
        status: 'OPEN'
      };
    } else if (isExit && openPositions[sym]) {
      const pos = openPositions[sym];
      pos.cikis_zaman = log.zaman;
      pos.cikis_fiyat = Number(log.fiyat);
      pos.status = 'CLOSED';
      
      const diff = pos.yön === 'LONG' ? (pos.cikis_fiyat - pos.giris_fiyat) : (pos.giris_fiyat - pos.cikis_fiyat);
      pos.pnl_yuzde = (diff / pos.giris_fiyat) * 100;
      
      // Süre (dakika)
      pos.sure_dk = Math.floor((new Date(pos.cikis_zaman).getTime() - new Date(pos.giris_zaman).getTime()) / 60000);
      
      closedTrades.push(pos);
      delete openPositions[sym];
    }
  });

  const activeTrades = Object.values(openPositions);
  
  // Hepsini birlestir, en yeniden eskiye sirala (UI gosterimi icin)
  const allTrades = [...activeTrades, ...closedTrades].sort((a, b) => new Date(b.giris_zaman) - new Date(a.giris_zaman));

  // Gunluk Istatistikler (Tüm kapalı islemler veya bugunun islemleri üzerinden)
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
      losses
    }
  };
}
