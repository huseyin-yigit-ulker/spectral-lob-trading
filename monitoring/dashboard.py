import time
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from datetime import datetime

class LiveMonitor:
    def __init__(self, refresh_rate: float = 1.0):
        self.refresh_rate = refresh_rate
        self.console = Console()
        self.data = {
            "price": 0.0,
            "spread": 0.0,
            "obi": 0.0,
            "cvd_1m": 0.0,
            "cvd_5m": 0.0,
            "position": 0.0,
            "pnl": 0.0,
            "recent_trades": [],
            "actions": []
        }

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="market_data"),
            Layout(name="agent_info")
        )
        
        # Header
        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="right")
        header.add_row(
            "Orders Signal Dashboard", 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        layout["header"].update(Panel(header, style="bold blue"))

        # Market Data
        market_table = Table(title="Market Metrics", expand=True)
        market_table.add_column("Metric", style="cyan")
        market_table.add_column("Value", style="magenta")
        market_table.add_row("Price", f"${self.data['price']:.2f}")
        market_table.add_row("Spread", f"${self.data['spread']:.2f}")
        market_table.add_row("OBI", f"{self.data['obi']:.4f}")
        market_table.add_row("CVD 1m", f"{self.data['cvd_1m']:.2f}")
        market_table.add_row("CVD 5m", f"{self.data['cvd_5m']:.2f}")
        layout["market_data"].update(Panel(market_table))

        # Agent Info
        agent_table = Table(title="Agent Status", expand=True)
        agent_table.add_column("Metric", style="cyan")
        agent_table.add_column("Value", style="green")
        agent_table.add_row("Position", f"{self.data['position']} BTC")
        agent_table.add_row("Unrealized PnL", f"${self.data['pnl']:.2f}")
        
        actions_str = "\n".join(self.data['actions'][-5:]) if self.data['actions'] else "No recent actions"
        
        layout["agent_info"].update(Panel(f"{agent_table}\n\nRecent Actions:\n{actions_str}"))
        
        return layout

    def update_data(self, new_data: dict):
        self.data.update(new_data)

    def run(self):
        with Live(self.generate_layout(), refresh_per_second=1/self.refresh_rate, screen=True) as live:
            try:
                while True:
                    live.update(self.generate_layout())
                    time.sleep(self.refresh_rate)
            except KeyboardInterrupt:
                pass
