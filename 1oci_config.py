# FILE: oci_config.py
import os
import oracledb
import logging

logger = logging.getLogger(__name__)

def init_oracle_client():
    """Initializes the Oracle DB client using wallet files for production."""
    if os.getenv('FLASK_ENV') == 'production':
        try:
            oracledb.init_oracle_client(
                lib_dir=os.getenv("ORACLE_LIB_DIR"), # e.g., for instant client
                config_dir=os.getenv("ORACLE_CONFIG_DIR") # Path to the unzipped wallet
            )
            logger.info("Oracle DB client initialized successfully for production.")
        except Exception as e:
            logger.error(f"Failed to initialize Oracle client. Ensure wallet path is correct. Error: {e}")
            raise
