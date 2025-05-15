import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Path to the session file
SESSION_FILE = os.path.join(os.path.dirname(__file__), "user_sessions.json")

def _load_sessions():
    """Load user sessions from file."""
    if not os.path.exists(SESSION_FILE):
        # Create initial empty sessions file
        with open(SESSION_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading session file: {e}")
        return {}

def _save_sessions(sessions):
    """Save user sessions to file."""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        return True
    except IOError as e:
        logger.error(f"Error saving session file: {e}")
        return False

def get_user_session(user_id):
    """Get a user's session by user_id."""
    sessions = _load_sessions()
    return sessions.get(str(user_id), {})

def update_user_session(user_id, data):
    """Update a user's session with new data."""
    sessions = _load_sessions()
    user_id = str(user_id)
    
    if user_id not in sessions:
        sessions[user_id] = {}
    
    # Update session with new data
    sessions[user_id].update(data)
    
    # Add last_updated timestamp
    sessions[user_id]['last_updated'] = datetime.now().isoformat()
    
    return _save_sessions(sessions)

def delete_user_session(user_id):
    """Delete a user's session."""
    sessions = _load_sessions()
    user_id = str(user_id)
    
    if user_id in sessions:
        del sessions[user_id]
        return _save_sessions(sessions)
    
    return True  # Session didn't exist, so technically it's deleted

def get_all_sessions():
    """Get all user sessions."""
    return _load_sessions()

def clear_old_sessions(days=30):
    """Clear sessions older than the specified number of days."""
    sessions = _load_sessions()
    now = datetime.now()
    removed = 0
    
    for user_id in list(sessions.keys()):
        last_updated_str = sessions[user_id].get('last_updated')
        if not last_updated_str:
            continue
            
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
            days_old = (now - last_updated).days
            
            if days_old > days:
                del sessions[user_id]
                removed += 1
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing date for user {user_id}: {e}")
    
    if removed > 0:
        _save_sessions(sessions)
        
    return removed