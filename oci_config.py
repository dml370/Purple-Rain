# FILE: oci_config.py
# Final, Unabridged Version: June 29, 2025

import os
import oracledb
import logging

logger = logging.getLogger(__name__)

def init_oracle_client():
    """
    Initializes the Oracle Database client using wallet files for secure,
    production-grade connections to an Oracle Autonomous Database.
    
    This function should be called once at application startup. It reads the
    wallet path and password from the environment variables.
    """
    wallet_path = os.getenv("ORACLE_WALLET_PATH")
    wallet_password = os.getenv("ORACLE_WALLET_PASSWORD")

    # Proceed only if the wallet path is configured in the .env file.
    # This allows the application to flexibly connect to other databases
    # (like the local Postgres for development) without this configuration.
    if wallet_path:
        logger.info(f"Oracle wallet path detected at '{wallet_path}'. Initializing Oracle thick client...")
        try:
            # This configures the python-oracledb driver to use the "Thick" mode
            # with all the necessary security configurations from your wallet.
            oracledb.init_oracle_client(
                config_dir=wallet_path,
                wallet_password=wallet_password
            )
            logger.info("Oracle DB client initialized successfully using connection wallet.")
        except Exception:
            logger.exception(
                "FATAL: Failed to initialize Oracle client with the provided wallet.\n"
                "Please ensure the 'ORACLE_WALLET_PATH' in your .env file points to the correct, "
                "unzipped wallet directory and 'ORACLE_WALLET_PASSWORD' is correct."
            )
            # Re-raise the exception to prevent the application from starting
            # with a broken database connection.
            raise
    else:
        logger.info("ORACLE_WALLET_PATH not set. Skipping Oracle thick client initialization.")
