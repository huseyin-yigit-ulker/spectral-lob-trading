import argparse
import sys
from rich.console import Console
from rich.panel import Panel

def print_banner():
    console = Console()
    banner = """
   ____rder     _____ignal
  / __ \       / ____|
 | |  | |_ __ | (___  
 | |  | | '__| \___ \ 
 | |__| | |    ____) |
  \____/|_|   |_____/ 
    Autonomous SMC Trading Agent
    """
    console.print(Panel(banner, style="bold green", expand=False))

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Orders Signal - Autonomous Trading Agent")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Collect
    collect_parser = subparsers.add_parser("collect", help="Start data collection")
    collect_parser.add_argument("--symbol", type=str, default="BTCUSDT")
    
    # Train
    train_parser = subparsers.add_parser("train", help="Train the RL agent")
    
    # Live
    live_parser = subparsers.add_parser("live", help="Run live trading (USE WITH CAUTION)")
    live_parser.add_argument("--symbol", type=str, default="BTCUSDT")
    live_parser.add_argument("--dry-run", action="store_true", help="Run without executing real trades")
    
    # Backtest
    backtest_parser = subparsers.add_parser("backtest", help="Run backtesting")
    
    # Monitor
    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring dashboard")

    args = parser.parse_args()

    if args.command == "collect":
        from scripts.collect_data import main as collect_main
        sys.argv = [sys.argv[0]] + (["--symbol", args.symbol] if args.symbol else [])
        collect_main()
    elif args.command == "train":
        print("Training module not yet implemented.")
    elif args.command == "live":
        print("WARNING: Starting live trading...")
        if args.dry_run:
            print("Running in DRY-RUN mode.")
        from scripts.run_agent import main as run_agent_main
        run_agent_main()
    elif args.command == "backtest":
        print("Backtesting module not yet implemented.")
    elif args.command == "monitor":
        from monitoring.dashboard import LiveMonitor
        monitor = LiveMonitor()
        monitor.run()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
