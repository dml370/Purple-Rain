import os
import json
import logging
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError as GoogleCloudError

logger = logging.getLogger(__name__)

class AIMemoryManager:
    def __init__(self):
        self.db = None
        self.user_id = None

    def initialize_firestore(self):
        """Initialize Firestore with proper authentication"""
        try:
            # Check for service account key
            key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'firestore-key.json')
            
            if os.path.exists(key_path):
                logger.info(f'Using service account key: {key_path}')
                credentials = service_account.Credentials.from_service_account_file(key_path)
                self.db = firestore.Client(credentials=credentials)
            else:
                logger.info('Using default application credentials')
                self.db = firestore.Client()
            
            # Test connection
            test_ref = self.db.collection('system').document('health_check')
            test_ref.set({
                'status': 'healthy',
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            logger.info('Firestore initialized successfully')
            return self.db
            
        except Exception as e:
            logger.error(f'Firestore initialization failed: {e}')
            return None

    def set_user(self, user_id):
        """Set current user for memory operations"""
        self.user_id = user_id
        
    def store_memory(self, memory_type, data, importance=5):
        """Store AI memory with importance rating"""
        if not self.db or not self.user_id:
            return False
        
        try:
            memory_data = {
                'type': memory_type,
                'data': data,
                'importance': importance,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': self.user_id
            }
            
            doc_ref = self.db.collection('ai_memories').document()
            doc_ref.set(memory_data)
            
            logger.info(f'Memory stored: {memory_type}')
            return True
            
        except Exception as e:
            logger.error(f'Failed to store memory: {e}')
            return False

    def retrieve_memories(self, memory_type, limit=100):
        """Retrieve memories by type"""
        if not self.db or not self.user_id:
            return []
        
        try:
            memories_ref = (self.db.collection('ai_memories')
                          .where('user_id', '==', self.user_id)
                          .where('type', '==', memory_type)
                          .order_by('timestamp', direction=firestore.Query.DESCENDING)
                          .limit(limit))
            
            memories = []
            for doc in memories_ref.stream():
                memory_data = doc.to_dict()
                memory_data['id'] = doc.id
                memories.append(memory_data)
            
            return memories
            
        except Exception as e:
            logger.error(f'Failed to retrieve memories: {e}')
            return []

    def store_conversation(self, message, response):
        """Store conversation exchange"""
        return self.store_memory('conversation', {
            'user_message': message,
            'ai_response': response
        }, importance=6)

# Global instance
memory_manager = AIMemoryManager()

def initialize_firestore():
    """Initialize the global memory manager"""
    return memory_manager.initialize_firestore()

def get_memory_manager():
    """Get the global memory manager instance"""
    return memory_manager