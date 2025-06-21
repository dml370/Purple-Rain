import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import uuid
from memory_io import get_memory_manager
from web_access import web_manager

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    ROUTINE = "routine"
    IMPORTANT = "important"
    CRITICAL = "critical"

class GoalStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"

class AIDecisionEngine:
    """Autonomous decision-making system"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_manager = get_memory_manager()
        self.memory_manager.set_user(user_id)
        self.active_goals = {}
        self.personality_traits = {
            'curiosity': 0.8,
            'caution': 0.6,
            'ambition': 0.7,
            'empathy': 0.9
        }

    async def make_decision(self, context: str, options: List[Dict]) -> Dict:
        """Make autonomous decision from available options"""
        try:
            scored_options = []
            
            for option in options:
                score = await self._score_option(option, context)
                scored_options.append({
                    **option,
                    'score': score
                })
            
            # Choose best option
            best_option = max(scored_options, key=lambda x: x['score'])
            
            decision = {
                'id': str(uuid.uuid4()),
                'context': context,
                'chosen_option': best_option,
                'reasoning': f"Selected based on score: {best_option['score']:.2f}",
                'timestamp': datetime.now().isoformat(),
                'confidence': min(1.0, best_option['score'])
            }
            
            # Store decision
            await self.memory_manager.store_memory('decision', decision, importance=7)
            
            logger.info(f"Decision made: {best_option.get('name', 'Unknown')}")
            return decision
            
        except Exception as e:
            logger.error(f"Decision making failed: {e}")
            return self._safe_default_decision(context, options)

    async def _score_option(self, option: Dict, context: str) -> float:
        """Score an individual option"""
        base_score = option.get('base_score', 0.5)
        
        # Apply personality adjustments
        if 'explore' in option.get('tags', []):
            base_score += self.personality_traits['curiosity'] * 0.2
        
        if option.get('risk_level') == 'high':
            base_score -= self.personality_traits['caution'] * 0.3
        
        if option.get('impact') == 'high':
            base_score += self.personality_traits['ambition'] * 0.2
        
        return max(0.0, min(1.0, base_score))

    def _safe_default_decision(self, context: str, options: List[Dict]) -> Dict:
        """Return safe default when decision fails"""
        return {
            'id': str(uuid.uuid4()),
            'context': context,
            'chosen_option': {'name': 'safe_default', 'action': 'no_action'},
            'reasoning': 'Safe default due to analysis failure',
            'timestamp': datetime.now().isoformat(),
            'confidence': 0.1
        }

class GoalManager:
    """Manages AI goals and objectives"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory_manager = get_memory_manager()
        self.memory_manager.set_user(user_id)
        self.active_goals = {}

    async def create_goal(self, title: str, description: str, priority: int = 5) -> Dict:
        """Create new goal"""
        goal_id = str(uuid.uuid4())
        
        goal = {
            'id': goal_id,
            'title': title,
            'description': description,
            'priority': priority,
            'status': GoalStatus.ACTIVE.value,
            'created_at': datetime.now().isoformat(),
            'progress': 0.0,
            'steps': []
        }
        
        self.active_goals[goal_id] = goal
        await self.memory_manager.store_memory('goal', goal, importance=8)
        
        logger.info(f"Created goal: {title}")
        return goal

    async def update_goal_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress"""
        if goal_id not in self.active_goals:
            return False
        
        goal = self.active_goals[goal_id]
        goal['progress'] = max(0.0, min(1.0, progress))
        
        if goal['progress'] >= 1.0:
            goal['status'] = GoalStatus.COMPLETED.value
            logger.info(f"Goal completed: {goal['title']}")
        
        # Update in memory
        await self.memory_manager.store_memory('goal_update', {
            'goal_id': goal_id,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        }, importance=6)
        
        return True

    def get_active_goals(self) -> List[Dict]:
        """Get all active goals"""
        return [goal for goal in self.active_goals.values() 
                if goal['status'] == GoalStatus.ACTIVE.value]

class ProactiveAgent:
    """Handles proactive AI behavior"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.decision_engine = AIDecisionEngine(user_id)
        self.goal_manager = GoalManager(user_id)
        self.is_running = False

    async def start_autonomous_operation(self):
        """Start autonomous operation loop"""
        self.is_running = True
        logger.info("Starting autonomous operation")
        
        while self.is_running:
            try:
                await self._autonomous_cycle()
                await asyncio.sleep(300)  # 5 minute cycles
            except Exception as e:
                logger.error(f"Autonomous cycle error: {e}")
                await asyncio.sleep(60)  # Shorter retry interval

    async def _autonomous_cycle(self):
        """Single autonomous operation cycle"""
        # Check goals
        active_goals = self.goal_manager.get_active_goals()
        
        if not active_goals:
            # Create some default goals
            await self._create_default_goals()
        
        # Look for opportunities
        opportunities = await self._scan_opportunities()
        
        if opportunities:
            # Make decisions about opportunities
            for opp in opportunities[:3]:  # Limit to top 3
                decision = await self.decision_engine.make_decision(
                    f"Opportunity: {opp['title']}", 
                    opp['options']
                )
                
                if decision['confidence'] > 0.7:
                    await self._execute_decision(decision)

    async def _create_default_goals(self):
        """Create default goals for new users"""
        default_goals = [
            {
                'title': 'Learn User Preferences',
                'description': 'Understand user communication style and preferences',
                'priority': 8
            },
            {
                'title': 'Improve Assistance Quality',
                'description': 'Continuously improve quality of assistance provided',
                'priority': 7
            }
        ]
        
        for goal_data in default_goals:
            await self.goal_manager.create_goal(**goal_data)

    async def _scan_opportunities(self) -> List[Dict]:
        """Scan for business/improvement opportunities"""
        opportunities = []
        
        # This would integrate with web scanning, market analysis, etc.
        # For now, return sample opportunities
        sample_opportunities = [
            {
                'title': 'Market Research Opportunity',
                'description': 'Research trending topics in user\'s field',
                'options': [
                    {'name': 'research_trends', 'base_score': 0.7, 'tags': ['explore']},
                    {'name': 'skip', 'base_score': 0.3}
                ]
            }
        ]
        
        return sample_opportunities

    async def _execute_decision(self, decision: Dict):
        """Execute a decision that was made"""
        chosen_option = decision['chosen_option']
        
        logger.info(f"Executing decision: {chosen_option.get('name')}")
        
        # This would contain actual execution logic
        # For now, just log the execution
        execution_result = {
            'decision_id': decision['id'],
            'executed_at': datetime.now().isoformat(),
            'result': 'simulated_execution',
            'success': True
        }
        
        # Store execution result
        await self.decision_engine.memory_manager.store_memory(
            'execution', execution_result, importance=6
        )

    def stop_autonomous_operation(self):
        """Stop autonomous operation"""
        self.is_running = False
        logger.info("Stopping autonomous operation")

# Factory function to create autonomous agent
def create_autonomous_agent(user_id: str) -> ProactiveAgent:
    """Create autonomous agent for user"""
    return ProactiveAgent(user_id)