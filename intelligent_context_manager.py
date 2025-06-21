import os
import json
import time
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import sqlite3
import logging

@dataclass
class ConversationTurn:
    """Single conversation turn with metadata"""
    user_id: str
    message: str
    response: str
    timestamp: float
    message_hash: str
    context_summary: str
    importance_score: float
    topic_tags: List[str]
    memory_type: str  # 'ephemeral', 'working', 'long_term'

@dataclass
class ContextSummary:
    """Compressed context summary for AI provider"""
    current_topic: str
    key_facts: List[str]
    user_preferences: Dict[str, str]
    recent_context: str
    conversation_goal: str

class IntelligentContextManager:
    """Manages conversation context locally, minimizes external API calls"""

    def __init__(self, db_path: str = "context_memory.db"):
        self.db_path = db_path
        self.max_working_memory = 10  # Keep last 10 interactions in working memory
        self.max_context_chars = 2000  # Maximum chars to send to AI provider
        self.working_memory = deque(maxlen=self.max_working_memory)
        self.topic_keywords = {}
        self.user_profiles = {}
        
        self.setup_database()
        self.logger = logging.getLogger(__name__)

    def setup_database(self):
        """Initialize local context database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversation turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp REAL NOT NULL,
                message_hash TEXT NOT NULL,
                context_summary TEXT,
                importance_score REAL DEFAULT 5.0,
                topic_tags TEXT,
                memory_type TEXT DEFAULT 'working',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                preferences TEXT,
                conversation_style TEXT,
                key_facts TEXT,
                topics_of_interest TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Context summaries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                topic_focus TEXT,
                time_period_start REAL,
                time_period_end REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    def calculate_importance_score(self, message: str, response: str) -> float:
        """Calculate importance score for conversation turn"""
        score = 5.0  # Base score
        
        # Increase score for certain keywords
        important_keywords = [
            'remember', 'important', 'goal', 'project', 'deadline',
            'preference', 'like', 'dislike', 'always', 'never',
            'configure', 'setup', 'error', 'problem', 'solution'
        ]
        
        text = (message + " " + response).lower()
        for keyword in important_keywords:
            if keyword in text:
                score += 1.0
        
        # Increase score for questions (likely to be referenced later)
        if '?' in message:
            score += 1.0
        
        # Increase score for longer, detailed responses
        if len(response) > 500:
            score += 1.0
        
        # Decrease score for very short exchanges
        if len(message) < 20 and len(response) < 50:
            score -= 1.0
        
        return min(max(score, 1.0), 10.0)  # Clamp between 1-10

    def extract_topic_tags(self, message: str, response: str) -> List[str]:
        """Extract topic tags from conversation"""
        text = (message + " " + response).lower()
        
        # Technical topics
        tech_keywords = {
            'programming': ['code', 'programming', 'python', 'javascript', 'api'],
            'ai': ['ai', 'artificial intelligence', 'machine learning', 'model'],
            'business': ['business', 'strategy', 'market', 'revenue', 'profit'],
            'security': ['security', 'authentication', 'encryption', 'password'],
            'database': ['database', 'sql', 'query', 'data'],
            'web': ['web', 'html', 'css', 'frontend', 'backend'],
            'deployment': ['deploy', 'server', 'production', 'hosting']
        }
        
        tags = []
        for topic, keywords in tech_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(topic)
        
        return tags

    def generate_context_summary(self, user_id: str, recent_turns: List[ConversationTurn]) -> str:
        """Generate compressed context summary"""
        if not recent_turns:
            return "New conversation"
        
        # Get current topic from most recent turns
        recent_tags = []
        for turn in recent_turns[-3:]:  # Last 3 turns
            recent_tags.extend(turn.topic_tags)
        
        current_topic = max(set(recent_tags), key=recent_tags.count) if recent_tags else "general"
        
        # Extract key points from recent conversation
        key_points = []
        for turn in recent_turns:
            if turn.importance_score > 7.0:
                # Extract first sentence of high-importance responses
                first_sentence = turn.response.split('.')[0][:100]
                if first_sentence and len(first_sentence) > 20:
                    key_points.append(first_sentence)
        
        # Build summary
        summary_parts = [f"Topic: {current_topic}"]
        if key_points:
            summary_parts.append(f"Key points: {'; '.join(key_points[:3])}")
        
        return " | ".join(summary_parts)[:500]  # Limit summary length

    def store_conversation_turn(self, user_id: str, message: str, response: str) -> ConversationTurn:
        """Store conversation turn locally"""
        timestamp = time.time()
        message_hash = hashlib.md5((message + str(timestamp)).encode()).hexdigest()
        
        # Calculate metadata
        importance_score = self.calculate_importance_score(message, response)
        topic_tags = self.extract_topic_tags(message, response)
        
        # Generate context summary from recent history
        recent_turns = list(self.working_memory)
        context_summary = self.generate_context_summary(user_id, recent_turns)
        
        # Determine memory type based on importance
        if importance_score > 8.0:
            memory_type = 'long_term'
        elif importance_score > 6.0:
            memory_type = 'working'
        else:
            memory_type = 'ephemeral'
        
        # Create conversation turn
        turn = ConversationTurn(
            user_id=user_id,
            message=message,
            response=response,
            timestamp=timestamp,
            message_hash=message_hash,
            context_summary=context_summary,
            importance_score=importance_score,
            topic_tags=topic_tags,
            memory_type=memory_type
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversation_turns 
            (user_id, message, response, timestamp, message_hash, context_summary, 
             importance_score, topic_tags, memory_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, message, response, timestamp, message_hash, context_summary,
            importance_score, json.dumps(topic_tags), memory_type
        ))
        conn.commit()
        conn.close()
        
        # Add to working memory
        self.working_memory.append(turn)
        
        self.logger.info(f"Stored conversation turn for user {user_id}, importance: {importance_score}")
        return turn

    def get_relevant_context(self, user_id: str, current_message: str, max_chars: int = None) -> ContextSummary:
        """Get relevant context for AI provider (minimal, focused)"""
        max_chars = max_chars or self.max_context_chars
        
        # Get recent working memory
        recent_turns = [turn for turn in self.working_memory if turn.user_id == user_id]
        
        # Get high-importance historical context
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message, response, topic_tags, importance_score
            FROM conversation_turns 
            WHERE user_id = ? AND importance_score > 7.0 AND memory_type IN ('working', 'long_term')
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (user_id,))
        
        important_history = cursor.fetchall()
        conn.close()
        
        # Extract current topic from message
        current_tags = self.extract_topic_tags(current_message, "")
        current_topic = current_tags[0] if current_tags else "general"
        
        # Build key facts from important history
        key_facts = []
        for hist in important_history:
            if hist[3] > 8.0:  # Very important
                fact = hist[1][:100].split('.')[0]  # First sentence only
                if fact and len(fact) > 20:
                    key_facts.append(fact)
        
        # Get user preferences
        user_prefs = self.get_user_preferences(user_id)
        
        # Build recent context (only essential info)
        recent_context_parts = []
        for turn in recent_turns[-2:]:  # Only last 2 turns
            if turn.importance_score > 6.0:
                recent_context_parts.append(f"User: {turn.message[:50]}... | AI: {turn.response[:50]}...")
        
        recent_context = " || ".join(recent_context_parts)
        
        # Determine conversation goal
        conversation_goal = self.infer_conversation_goal(current_message, recent_turns)
        
        context_summary = ContextSummary(
            current_topic=current_topic,
            key_facts=key_facts[:3],  # Limit to 3 most important facts
            user_preferences=user_prefs,
            recent_context=recent_context[:500],  # Limit recent context
            conversation_goal=conversation_goal
        )
        
        return context_summary

    def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        """Get user preferences from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT preferences FROM user_profiles WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                pass
        
        return {}

    def update_user_preferences(self, user_id: str, preferences: Dict[str, str]):
        """Update user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles (user_id, preferences, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user_id, json.dumps(preferences)))
        conn.commit()
        conn.close()

    def infer_conversation_goal(self, current_message: str, recent_turns: List[ConversationTurn]) -> str:
        """Infer what the user is trying to accomplish"""
        message_lower = current_message.lower()
        
        # Goal keywords
        goal_patterns = {
            'help_request': ['help', 'how to', 'can you', 'please'],
            'problem_solving': ['error', 'issue', 'problem', 'fix', 'debug'],
            'information_seeking': ['what is', 'explain', 'tell me about', 'describe'],
            'task_completion': ['create', 'build', 'make', 'generate', 'write'],
            'configuration': ['setup', 'configure', 'install', 'settings'],
            'learning': ['learn', 'understand', 'tutorial', 'guide', 'example']
        }
        
        for goal, keywords in goal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return goal
        
        # Check recent turn patterns
        if recent_turns:
            last_turn = recent_turns[-1]
            if 'programming' in last_turn.topic_tags or 'code' in last_turn.topic_tags:
                return 'programming_assistance'
        
        return 'general_conversation'

    def prepare_ai_context(self, user_id: str, current_message: str) -> str:
        """Prepare minimal context for AI provider"""
        context_summary = self.get_relevant_context(user_id, current_message)
        
        # Build compact context string
        context_parts = []
        
        # Add conversation goal
        if context_summary.conversation_goal != 'general_conversation':
            context_parts.append(f"Goal: {context_summary.conversation_goal}")
        
        # Add current topic
        if context_summary.current_topic != 'general':
            context_parts.append(f"Topic: {context_summary.current_topic}")
        
        # Add key facts (only if relevant to current message)
        if context_summary.key_facts:
            relevant_facts = []
            current_lower = current_message.lower()
            for fact in context_summary.key_facts:
                # Simple relevance check
                fact_words = set(fact.lower().split())
                message_words = set(current_lower.split())
                if fact_words.intersection(message_words):
                    relevant_facts.append(fact)
            
            if relevant_facts:
                context_parts.append(f"Context: {'; '.join(relevant_facts[:2])}")
        
        # Add user preferences (only relevant ones)
        if context_summary.user_preferences:
            relevant_prefs = []
            for key, value in context_summary.user_preferences.items():
                if key.lower() in current_message.lower():
                    relevant_prefs.append(f"{key}: {value}")
            
            if relevant_prefs:
                context_parts.append(f"Preferences: {'; '.join(relevant_prefs[:2])}")
        
        # Combine context (ensure it's under character limit)
        full_context = " | ".join(context_parts)
        
        if len(full_context) > self.max_context_chars:
            # Truncate to essential information
            essential_context = context_parts[0] if context_parts else ""
            return essential_context[:self.max_context_chars]
        
        return full_context

    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old ephemeral data"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete old ephemeral conversations
        cursor.execute("""
            DELETE FROM conversation_turns 
            WHERE timestamp < ? AND memory_type = 'ephemeral'
        """, (cutoff_time,))
        
        # Keep working memory for shorter time (7 days)
        working_cutoff = time.time() - (7 * 24 * 3600)
        cursor.execute("""
            DELETE FROM conversation_turns 
            WHERE timestamp < ? AND memory_type = 'working' AND importance_score < 6.0
        """, (working_cutoff,))
        
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        
        self.logger.info(f"Cleaned up {deleted_count} old conversation records")
        return deleted_count

    def get_conversation_stats(self, user_id: str) -> Dict:
        """Get conversation statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_turns,
                AVG(importance_score) as avg_importance,
                COUNT(DISTINCT topic_tags) as unique_topics,
                memory_type,
                COUNT(*) as count_by_type
            FROM conversation_turns 
            WHERE user_id = ?
            GROUP BY memory_type
        """, (user_id,))
        
        type_stats = cursor.fetchall()
        
        cursor.execute("""
            SELECT COUNT(*) FROM conversation_turns WHERE user_id = ?
        """, (user_id,))
        
        total = cursor.fetchone()[0]
        conn.close()
        
        return {
            'total_conversations': total,
            'memory_distribution': {row[3]: row[4] for row in type_stats},
            'average_importance': type_stats[0][1] if type_stats else 0,
            'working_memory_size': len(self.working_memory)
        }

# Integration class for Flask app
class ContextManagerIntegration:
    """Integration layer for Flask application"""

    def __init__(self, app=None):
        self.context_manager = IntelligentContextManager()
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        app.teardown_appcontext(self.cleanup)
        
        # Add cleanup job
        import atexit
        atexit.register(self.context_manager.cleanup_old_data)

    def cleanup(self, exception):
        """Cleanup on app context teardown"""
        pass

    def process_ai_interaction(self, user_id: str, user_message: str, ai_response: str) -> Dict:
        """Process AI interaction with minimal context transfer"""
        
        # Store the conversation locally
        turn = self.context_manager.store_conversation_turn(user_id, user_message, ai_response)
        
        # Get statistics
        stats = self.context_manager.get_conversation_stats(user_id)
        
        return {
            'conversation_stored': True,
            'importance_score': turn.importance_score,
            'memory_type': turn.memory_type,
            'topic_tags': turn.topic_tags,
            'context_summary': turn.context_summary,
            'stats': stats
        }

    def get_ai_context(self, user_id: str, current_message: str) -> str:
        """Get minimal context for AI provider"""
        return self.context_manager.prepare_ai_context(user_id, current_message)

    def get_context_summary(self, user_id: str) -> ContextSummary:
        """Get full context summary for internal use"""
        return self.context_manager.get_relevant_context(user_id, "")