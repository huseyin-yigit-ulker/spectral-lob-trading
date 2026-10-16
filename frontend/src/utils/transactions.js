import { reconstructTrades } from './tradeLogic';

export function calculateTransactions(logs, version = 'v5_5') {
  if (!logs || logs.length === 0) {
    return {
      closed: [],
      active: [],
      allTrades: [],
      stats: {
        totalPnl: 0,
        winRate: 0,
        totalClosed: 0,
        wins: 0,
        losses: 0,
        activeCount: 0,
        filteredCount: 0,
        preventedLossPnl: 0
      },
      filteredCount: 0,
      preventedLossPnl: 0
    };
  }

  const result = reconstructTrades(logs, version);

  // Return non-filtered closed trades for main display, while attaching full list & stats
  return {
    closed: result.closedTrades,
    active: result.activeTrades,
    allTrades: result.allTrades,
    stats: result.stats,
    filteredCount: result.stats.filteredCount,
    preventedLossPnl: result.stats.preventedLossPnl
  };
}
