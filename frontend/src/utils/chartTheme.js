// Binance-esinli koyu tema paleti
// ict-trade/chartTheme.js'den adapte edilmistir

export function readChartTheme() {
  return {
    bg: '#0B0E11',
    panel: '#1E2329',
    text: '#EAECEF',
    muted: '#848E9C',
    border: '#2B3139',
    up: '#0ECB81',
    down: '#F6465D',
    accent: '#F0B90B',
    upSoft: (a) => `rgba(14, 203, 129, ${a})`,
    downSoft: (a) => `rgba(246, 70, 93, ${a})`,
  };
}
