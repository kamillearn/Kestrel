"""Live/paper entrypoint.
    python scripts/run.py config/config.yaml [--live]   (default = dry-run)"""
import logging
import sys
from kestrel.config import load_config
from kestrel.risk.manager import RiskManager
from kestrel.live.runner import Runner

def make_broker(cfg):
    """Instantiates the correct broker based on the nested YAML config."""
    broker_name = cfg.broker.get("name", "").lower()
    
    if broker_name == "ibkr":
        from kestrel.execution.ibkr import IBKRBroker
        host = cfg.broker.get("host", "127.0.0.1")
        port = cfg.broker.get("port", 7497)
        client_id = cfg.broker.get("client_id", 1)
        
        logging.info(f"Connecting to IBKR Gateway at {host}:{port} (Client ID: {client_id})")
        return IBKRBroker(host=host, port=port, client_id=client_id)
        
    elif broker_name == "oanda":
        from kestrel.execution.oanda import OandaBroker
        return OandaBroker()
        
    else:
        raise ValueError(f"Unknown broker requested in config: '{broker_name}'")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s")
        
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    cfg = load_config(config_path)
    
    dry = "--live" not in sys.argv
    if dry:
        logging.info("Starting Kestrel in DRY-RUN mode. No real orders will be sent.")

    broker = make_broker(cfg)
    
    try:
        broker.connect()
        
        # Give IBKR 2 seconds to stream the account data back over the socket
        logging.info("Waiting for IBKR account synchronization...")
        broker_name = cfg.broker.get("name", "").lower()
        if broker_name == "ibkr":
            import ib_insync
            ib_insync.util.sleep(2.0)
        else:
            import time
            time.sleep(2.0)
        
        eq = broker.equity()
        
        # --- THE EQUITY FALLBACK FIX ---
        if eq <= 0.0:
            # If IBKR fails to send the balance in time, fallback to your 1,006,483 config
            # Ensure we safely grab the 'starting_capital' from the 'risk_management' block
            fallback = cfg.risk.get("starting_capital", 1006483.0) if hasattr(cfg, 'risk') else 1006483.0
            logging.warning(f"Broker returned $0.00 equity. Falling back to configured capital: ${fallback:,.2f}")
            eq = fallback
        else:
            logging.info(f"Pre-flight successful. Live Equity: ${eq:,.2f}")
            
        broker.disconnect()
        
        # Launch the main event loop
        Runner(cfg, broker, RiskManager(cfg.risk, eq), dry_run=dry).start()
        
    except Exception as e:
        # We use logging.exception() to print the FULL traceback if anything crashes!
        logging.exception("Fatal error during startup:")
        sys.exit(1)