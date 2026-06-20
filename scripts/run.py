"""
Kestrel Engine - Live Production Entry Point.
This script loads the configuration and initializes the broker/strategy.
"""
import logging
import argparse
import yaml
import time
from datetime import datetime
from kestrel.execution.ibkr import IBKRBroker
from kestrel.execution.oanda import OandaBroker

def make_broker(cfg):
    """Instantiates the correct broker based on the nested YAML config."""
    broker_name = cfg.get("broker", {}).get("name", "").lower()
    
    if broker_name == "ibkr":
        host = cfg["broker"].get("host", "127.0.0.1")
        port = cfg["broker"].get("port", 7497)
        client_id = cfg["broker"].get("client_id", 1)
        return IBKRBroker(host=host, port=port, client_id=client_id)
        
    elif broker_name == "oanda":
        # Extract from config dictionary
        broker_cfg = cfg.get("broker", {})
        env = broker_cfg.get("env", "practice")
        token = broker_cfg.get("token")
        account_id = broker_cfg.get("account_id")
        
        # Explicitly pass the arguments
        return OandaBroker(env=env, account_id=account_id, token=token)
        
    else:
        raise ValueError(f"Unknown broker requested in config: '{broker_name}'")

# --- MAIN EXECUTION LOGIC ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", help="Path to the YAML config file")
    parser.add_argument("--live", action="store_true", help="Run in live execution mode")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logging.info(f"Loading config from: {args.config_path}")
    
    with open(args.config_path, 'r') as f:
        cfg = yaml.safe_load(f)

    # 1. Initialize the broker
    broker = make_broker(cfg)
    
    # 2. Connect to the API
    broker.connect()
    
    # 3. Fetch Equity to verify it works
    eq = broker.equity()
    
    logging.info(f"Pre-flight successful. Live Equity: ${eq:,.2f}")
    logging.info("Kestrel Engine is ready for execution.")
    
    # Extract instruments to watch from config
    instruments_to_watch = cfg.get("instruments", [])
    logging.info(f"Loaded Portfolio: {instruments_to_watch}")
    
    # 4. The Main Event Loop
    logging.info("Entering continuous monitoring loop. Press Ctrl+C to stop.")
    
    loop_count = 0
    try:
        while True:
            # ---------------------------------------------------------
            # 🚀 CORE TRADING LOGIC GOES HERE
            # 1. Check current time against Session Open
            # 2. Wait for Opening Range to complete
            # 3. Calculate OR High/Low
            # 4. Place OCO Bracket Orders
            # 5. Monitor and flatten at End of Day
            # ---------------------------------------------------------
            
            # Print a heartbeat to the terminal every 60 seconds
            if loop_count % 60 == 0:
                now = datetime.now().strftime("%H:%M:%S")
                logging.info(f"[{now}] Heartbeat: Engine is actively watching markets...")
            
            loop_count += 1
            time.sleep(1) # Sleep 1 second to prevent pinning the CPU at 100%
            
    except KeyboardInterrupt:
        print("\n")
        logging.info("🛑 KeyboardInterrupt received (Ctrl+C). Initiating graceful shutdown...")
    except Exception as e:
        logging.error(f"❌ Fatal crash in event loop: {e}")
    finally:
        logging.info("Disconnecting from broker...")
        broker.disconnect()
        logging.info("Kestrel Engine shutdown complete. Goodbye!")