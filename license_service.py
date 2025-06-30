# FILE: services/license_service.py
# ... imports ...

def validate_license_key(license_key: str) -> bool:
    """Validates a license key, now with a grace period concept."""
    if not license_key:
        logger.error("LICENSE VALIDATION FAILED: No license key provided.")
        return False
    try:
        # The app can check the timestamp and decide if it's within a grace period
        # e.g., if (time.time() - issued_at) > GRACE_PERIOD_SECONDS:
        decrypted_payload = cipher_suite.decrypt(license_key.encode(), ttl=None)
        user_id, timestamp_str = decrypted_payload.decode().split('|')
        logger.info(f"License successfully validated for user_id: {user_id}")
        return True
    except Exception as e:
        logger.error(f"LICENSE VALIDATION FAILED: {e}")
        return False
