"""
Session management system for GraphRAG API Service.

This module provides comprehensive session management with concurrent
session limits, device tracking, and security monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel

from ..exceptions import AuthenticationError, QuotaExceededError
from ..security import get_security_logger


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


class DeviceType(str, Enum):
    """Device type enumeration."""
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    DESKTOP = "desktop"
    UNKNOWN = "unknown"


class Session(BaseModel):
    """User session model."""
    
    session_id: str
    user_id: str
    device_info: Optional[str] = None
    device_type: DeviceType = DeviceType.UNKNOWN
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None
    
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    
    status: SessionStatus = SessionStatus.ACTIVE
    refresh_token_id: Optional[str] = None
    
    # Security tracking
    login_attempts: int = 0
    suspicious_activity_count: int = 0
    last_suspicious_activity: Optional[datetime] = None
    
    # Session metadata
    permissions: List[str] = []
    roles: List[str] = []
    workspace_id: Optional[str] = None


class SessionConfig(BaseModel):
    """Session configuration."""
    
    max_sessions_per_user: int = 5
    session_timeout_minutes: int = 30
    max_idle_time_minutes: int = 15
    require_device_verification: bool = False
    track_location: bool = False
    suspicious_activity_threshold: int = 3


class SessionManager:
    """Comprehensive session management system."""
    
    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.security_logger = get_security_logger()
        
        # In-memory session storage (would be Redis/database in production)
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids
        self._refresh_token_sessions: Dict[str, str] = {}  # refresh_token_id -> session_id
    
    async def create_session(
        self,
        user_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        refresh_token_id: Optional[str] = None
    ) -> Session:
        """Create a new user session.
        
        Args:
            user_id: User identifier
            device_info: Device information
            ip_address: Client IP address
            user_agent: User agent string
            permissions: User permissions
            roles: User roles
            workspace_id: Associated workspace
            refresh_token_id: Associated refresh token
            
        Returns:
            Created session
            
        Raises:
            QuotaExceededError: If user has too many active sessions
        """
        # Check session limits
        await self._check_session_limits(user_id)
        
        # Create session
        session_id = str(uuid4())
        now = datetime.utcnow()
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            device_info=device_info,
            device_type=self._detect_device_type(user_agent),
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(minutes=self.config.session_timeout_minutes),
            refresh_token_id=refresh_token_id,
            permissions=permissions or [],
            roles=roles or [],
            workspace_id=workspace_id
        )
        
        # Store session
        self._sessions[session_id] = session
        
        # Update user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        # Map refresh token to session
        if refresh_token_id:
            self._refresh_token_sessions[refresh_token_id] = session_id
        
        # Log session creation
        self.security_logger.authentication_attempt(
            success=True,
            user_id=user_id,
            method="session_create"
        )
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        
        if not session:
            return None
        
        # Check if session is expired or revoked
        if session.status != SessionStatus.ACTIVE:
            return None
        
        # Check expiration
        if session.expires_at < datetime.utcnow():
            await self._expire_session(session_id)
            return None
        
        # Check idle timeout
        idle_time = datetime.utcnow() - session.last_activity
        if idle_time.total_seconds() > (self.config.max_idle_time_minutes * 60):
            await self._expire_session(session_id)
            return None
        
        return session
    
    async def update_session_activity(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Update session last activity."""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        now = datetime.utcnow()
        session.last_activity = now
        
        # Extend session if needed
        if session.expires_at - now < timedelta(minutes=5):
            session.expires_at = now + timedelta(minutes=self.config.session_timeout_minutes)
        
        # Check for suspicious activity
        if ip_address and session.ip_address and ip_address != session.ip_address:
            await self._flag_suspicious_activity(session, "ip_change")
        
        if user_agent and session.user_agent and user_agent != session.user_agent:
            await self._flag_suspicious_activity(session, "user_agent_change")
        
        return True
    
    async def revoke_session(self, session_id: str, reason: str = "manual") -> bool:
        """Revoke a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.REVOKED
        
        # Remove from active sessions
        if session.user_id in self._user_sessions:
            try:
                self._user_sessions[session.user_id].remove(session_id)
            except ValueError:
                pass
        
        # Remove refresh token mapping
        if session.refresh_token_id:
            self._refresh_token_sessions.pop(session.refresh_token_id, None)
        
        # Log session revocation
        self.security_logger.authentication_attempt(
            success=True,
            user_id=session.user_id,
            method="session_revoke"
        )
        
        return True
    
    async def revoke_user_sessions(
        self,
        user_id: str,
        except_session_id: Optional[str] = None
    ) -> int:
        """Revoke all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, []).copy()
        revoked_count = 0
        
        for session_id in session_ids:
            if session_id != except_session_id:
                if await self.revoke_session(session_id, "user_revoke_all"):
                    revoked_count += 1
        
        return revoked_count
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        
        for session_id in session_ids.copy():
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
            else:
                # Remove invalid session
                try:
                    self._user_sessions[user_id].remove(session_id)
                except ValueError:
                    pass
        
        return sessions
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            if (session.expires_at < now or 
                session.status != SessionStatus.ACTIVE or
                (now - session.last_activity).total_seconds() > (self.config.max_idle_time_minutes * 60)):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._expire_session(session_id)
        
        return len(expired_sessions)
    
    async def get_session_by_refresh_token(self, refresh_token_id: str) -> Optional[Session]:
        """Get session by refresh token ID."""
        session_id = self._refresh_token_sessions.get(refresh_token_id)
        if not session_id:
            return None
        
        return await self.get_session(session_id)
    
    async def _check_session_limits(self, user_id: str):
        """Check if user can create new session."""
        active_sessions = await self.get_user_sessions(user_id)
        
        if len(active_sessions) >= self.config.max_sessions_per_user:
            # Revoke oldest session
            oldest_session = min(active_sessions, key=lambda s: s.last_activity)
            await self.revoke_session(oldest_session.session_id, "session_limit")
    
    async def _expire_session(self, session_id: str):
        """Mark session as expired."""
        session = self._sessions.get(session_id)
        if session:
            session.status = SessionStatus.EXPIRED
            
            # Remove from active sessions
            if session.user_id in self._user_sessions:
                try:
                    self._user_sessions[session.user_id].remove(session_id)
                except ValueError:
                    pass
            
            # Remove refresh token mapping
            if session.refresh_token_id:
                self._refresh_token_sessions.pop(session.refresh_token_id, None)
    
    async def _flag_suspicious_activity(self, session: Session, activity_type: str):
        """Flag suspicious activity on session."""
        session.suspicious_activity_count += 1
        session.last_suspicious_activity = datetime.utcnow()
        
        # Log suspicious activity
        self.security_logger.suspicious_activity(
            activity_type=activity_type,
            description=f"Suspicious activity detected in session {session.session_id}",
            user_id=session.user_id
        )
        
        # Mark session as suspicious if threshold exceeded
        if session.suspicious_activity_count >= self.config.suspicious_activity_threshold:
            session.status = SessionStatus.SUSPICIOUS
            
            # Optionally revoke session
            await self.revoke_session(session.session_id, "suspicious_activity")
    
    def _detect_device_type(self, user_agent: Optional[str]) -> DeviceType:
        """Detect device type from user agent."""
        if not user_agent:
            return DeviceType.UNKNOWN
        
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone", "ipad"]):
            return DeviceType.MOBILE
        elif any(api in user_agent_lower for api in ["curl", "wget", "python", "postman"]):
            return DeviceType.API
        elif any(desktop in user_agent_lower for desktop in ["electron", "desktop"]):
            return DeviceType.DESKTOP
        else:
            return DeviceType.WEB


# Global session manager
_session_manager = SessionManager()


# Utility functions
async def create_session(
    user_id: str,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    permissions: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    workspace_id: Optional[str] = None,
    refresh_token_id: Optional[str] = None
) -> Session:
    """Create session using global session manager."""
    return await _session_manager.create_session(
        user_id, device_info, ip_address, user_agent,
        permissions, roles, workspace_id, refresh_token_id
    )


async def get_session(session_id: str) -> Optional[Session]:
    """Get session using global session manager."""
    return await _session_manager.get_session(session_id)


async def revoke_session(session_id: str, reason: str = "manual") -> bool:
    """Revoke session using global session manager."""
    return await _session_manager.revoke_session(session_id, reason)


async def get_user_sessions(user_id: str) -> List[Session]:
    """Get user sessions using global session manager."""
    return await _session_manager.get_user_sessions(user_id)
