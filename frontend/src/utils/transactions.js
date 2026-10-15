export function calculateTransactions(logs) {
  const closed = [];
  const active = [];
  const groups = {};

  // Group by symbol
  logs.forEach(log => {
    if (!groups[log.sembol]) {
      groups[log.sembol] = [];
    }
    groups[log.sembol].push(log);
  });

  for (const symbol in groups) {
    let state = 'NO_POSITION';
    let entryPrice = 0;
    let entryTime = null;
    let entryRegime = 'NEUTRAL';
    let entryReason = '';
    let entryIsSniper = false;

    // Ensure sorted by time ASC
    const symbolLogs = groups[symbol].sort((a, b) => new Date(a.zaman) - new Date(b.zaman));

    symbolLogs.forEach(row => {
      const sig = row.sinyal;
      const fiyat = parseFloat(row.fiyat);
      const zaman = row.zaman;

      if (state === 'NO_POSITION') {
        const isSniper = row.entry_reason ? row.entry_reason.toLowerCase().includes('sniper') : (Math.abs(Number(row.obi || 0)) >= 0.70 && Number(row.fvg_depth || 0) >= 0.40);
        entryIsSniper = isSniper;

        if (sig === '[+] AL (LONG)') {
          state = 'IN_LONG';
          entryPrice = fiyat;
          entryTime = zaman;
          entryRegime = row.btc_regime || (isSniper ? 'BEARISH' : 'NEUTRAL');
          entryReason = row.entry_reason || (isSniper ? `Sniper İstisnası: Altcoin BTC'den Pozitif Ayrıştı (OBI: ${Number(row.obi || 0) > 0 ? '+' : ''}${Number(row.obi || 0).toFixed(2)})` : `BTC Trend Uyumlu (${entryRegime})`);
        } else if (sig === '[-] SAT (SHORT)') {
          state = 'IN_SHORT';
          entryPrice = fiyat;
          entryTime = zaman;
          entryRegime = row.btc_regime || (isSniper ? 'BULLISH' : 'NEUTRAL');
          entryReason = row.entry_reason || (isSniper ? `Sniper İstisnası: Altcoin BTC'den Negatif Ayrıştı (OBI: ${Number(row.obi || 0) > 0 ? '+' : ''}${Number(row.obi || 0).toFixed(2)})` : `BTC Trend Uyumlu (${entryRegime})`);
        }
      } else if (state === 'IN_LONG') {
        if (sig === '[!] BEKLE' || sig === '[-] SAT (SHORT)') {
          const pnlPct = ((fiyat - entryPrice) / entryPrice) * 100;
          closed.push({
            sembol: symbol,
            tip: 'LONG',
            entry_time: entryTime,
            exit_time: zaman,
            entry_price: entryPrice,
            exit_price: fiyat,
            pnl_pct: pnlPct,
            win: pnlPct > 0,
            obi: row.obi,
            fvg_depth: row.fvg_depth,
            btc_regime: entryRegime,
            entry_reason: entryReason,
            is_sniper: entryIsSniper
          });
          if (sig === '[-] SAT (SHORT)') {
            state = 'IN_SHORT';
            entryPrice = fiyat;
            entryTime = zaman;
            const isSniper = row.entry_reason ? row.entry_reason.toLowerCase().includes('sniper') : (Math.abs(Number(row.obi || 0)) >= 0.70 && Number(row.fvg_depth || 0) >= 0.40);
            entryIsSniper = isSniper;
            entryRegime = row.btc_regime || (isSniper ? 'BULLISH' : 'NEUTRAL');
            entryReason = row.entry_reason || (isSniper ? `Sniper İstisnası: Altcoin BTC'den Negatif Ayrıştı` : `BTC Trend Uyumlu (${entryRegime})`);
          } else {
            state = 'NO_POSITION';
          }
        }
      } else if (state === 'IN_SHORT') {
        if (sig === '[!] BEKLE' || sig === '[+] AL (LONG)') {
          const pnlPct = ((entryPrice - fiyat) / entryPrice) * 100;
          closed.push({
            sembol: symbol,
            tip: 'SHORT',
            entry_time: entryTime,
            exit_time: zaman,
            entry_price: entryPrice,
            exit_price: fiyat,
            pnl_pct: pnlPct,
            win: pnlPct > 0,
            obi: row.obi,
            fvg_depth: row.fvg_depth,
            btc_regime: entryRegime,
            entry_reason: entryReason,
            is_sniper: entryIsSniper
          });
          if (sig === '[+] AL (LONG)') {
            state = 'IN_LONG';
            entryPrice = fiyat;
            entryTime = zaman;
            const isSniper = row.entry_reason ? row.entry_reason.toLowerCase().includes('sniper') : (Math.abs(Number(row.obi || 0)) >= 0.70 && Number(row.fvg_depth || 0) >= 0.40);
            entryIsSniper = isSniper;
            entryRegime = row.btc_regime || (isSniper ? 'BEARISH' : 'NEUTRAL');
            entryReason = row.entry_reason || (isSniper ? `Sniper İstisnası: Altcoin BTC'den Pozitif Ayrıştı` : `BTC Trend Uyumlu (${entryRegime})`);
          } else {
            state = 'NO_POSITION';
          }
        }
      }
    });
    // Check for active trade at the end of the logs
    if (state === 'IN_LONG') {
      active.push({
        sembol: symbol,
        tip: 'LONG',
        entry_time: entryTime,
        entry_price: entryPrice,
        btc_regime: entryRegime,
        entry_reason: entryReason,
        is_sniper: entryIsSniper
      });
    } else if (state === 'IN_SHORT') {
      active.push({
        sembol: symbol,
        tip: 'SHORT',
        entry_time: entryTime,
        entry_price: entryPrice,
        btc_regime: entryRegime,
        entry_reason: entryReason,
        is_sniper: entryIsSniper
      });
    }
  }

  // Sort trades by exit_time DESC
  closed.sort((a, b) => new Date(b.exit_time) - new Date(a.exit_time));
  return { closed, active };
}
