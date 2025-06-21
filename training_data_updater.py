import os
import json
import time
import logging

logging.basicConfig(level=logging.INFO)

DATA_STORE = 'assistant_memory.json'

def load_memory():
    """Load stored memory data from a JSON file."""
    try:
        with open(DATA_STORE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"entries": []}

def save_memory(data):
    """Save the assistant's memory data to a JSON file."""
    with open(DATA_STORE, 'w') as f:
        json.dump(data, f, indent=4)

def prune_obsolete_data():
    """Remove memory entries older than 30 days."""
    memory = load_memory()
    current_time = time.time()
    if "entries" in memory:
        memory["entries"] = [
            entry for entry in memory["entries"]
            if current_time - entry.get("timestamp", 0) < 30 * 24 * 3600
        ]
    save_memory(memory)
    logging.info("Obsolete training data pruned.")

if __name__ == '__main__':
    prune_obsolete_data()