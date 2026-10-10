export function calculateTransactions(logs) {
  const trades = [];
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

    // Ensure sorted by time ASC
    const symbolLogs = groups[symbol].sort((a, b) => new Date(a.zaman) - new Date(b.zaman));

    symbolLogs.forEach(row => {
      const sig = row.sinyal;
      const fiyat = parseFloat(row.fiyat);
      const zaman = row.zaman;

      if (state === 'NO_POSITION') {
        if (sig === '[+] AL (LONG)') {
          state = 'IN_LONG';
          entryPrice = fiyat;
          entryTime = zaman;
        } else if (sig === '[-] SAT (SHORT)') {
          state = 'IN_SHORT';
          entryPrice = fiyat;
          entryTime = zaman;
        }
      } else if (state === 'IN_LONG') {
        if (sig === '[!] BEKLE' || sig === '[-] SAT (SHORT)') {
          const pnlPct = ((fiyat - entryPrice) / entryPrice) * 100;
          trades.push({
            sembol: symbol,
            tip: 'LONG',
            entry_time: entryTime,
            exit_time: zaman,
            entry_price: entryPrice,
            exit_price: fiyat,
            pnl_pct: pnlPct,
            win: pnlPct > 0
          });
          if (sig === '[-] SAT (SHORT)') {
            state = 'IN_SHORT';
            entryPrice = fiyat;
            entryTime = zaman;
          } else {
            state = 'NO_POSITION';
          }
        }
      } else if (state === 'IN_SHORT') {
        if (sig === '[!] BEKLE' || sig === '[+] AL (LONG)') {
          const pnlPct = ((entryPrice - fiyat) / entryPrice) * 100;
          trades.push({
            sembol: symbol,
            tip: 'SHORT',
            entry_time: entryTime,
            exit_time: zaman,
            entry_price: entryPrice,
            exit_price: fiyat,
            pnl_pct: pnlPct,
            win: pnlPct > 0
          });
          if (sig === '[+] AL (LONG)') {
            state = 'IN_LONG';
            entryPrice = fiyat;
            entryTime = zaman;
          } else {
            state = 'NO_POSITION';
          }
        }
      }
    });
  }

  // Sort trades by exit_time DESC
  return trades.sort((a, b) => new Date(b.exit_time) - new Date(a.exit_time));
}
