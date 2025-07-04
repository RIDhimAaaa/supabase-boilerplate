"""
RBAC dependencies for FastAPI routes
Role-based access control implemented as dependencies that run after authentication
"""
from fastapi import Depends, HTTPException, status, Request
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

RESOURCES_FOR_ROLES = {
    'admin': {
        'admin': ['read', 'write', 'delete'], 
        'users': ['read', 'write', 'delete'], 
        'users/profiles': ['read', 'write', 'delete'], 
        'users/search': ['read'], 
        'analytics': ['read'],  
        'settings': ['read', 'write'], 
        'content': ['read', 'write', 'delete'],  
        'reports': ['read', 'write'],  
    },
    'user': {
        'users/me': ['read', 'write'], 
        'users/profiles': ['read'], 
        'content': ['read', 'write'],  
    }
}

def normalize_path(path: str) -> str:
    """Normalize request path for RBAC checking"""    
    if path.startswith('/'):
        path = path[1:]

    segments = path.split('/')
    
    if len(segments) == 0:
        return path
    
    if segments[0] == 'admin':
        if len(segments) >= 2:
            return f'admin/{segments[1]}'
        return 'admin'
    
    elif segments[0] == 'users':
        if len(segments) >= 2:
            if segments[1] == 'me':
                return 'users/me'
            elif segments[1] == 'profile' or segments[1] == 'profiles':
                return 'users/profiles'
            elif segments[1] == 'search':
                return 'users/search'
        return 'users'
    
    elif segments[0] == 'analytics':
        return 'analytics'
    
    elif segments[0] == 'settings':
        return 'settings'
    
    elif segments[0] == 'content':
        return 'content'
    
    elif segments[0] == 'reports':
        return 'reports'
    
    return segments[0]

def translate_method_to_action(method: str) -> str:
    """Map HTTP methods to RBAC actions"""
    method_permission_mapping = {
        'GET': 'read',
        'POST': 'write',
        'PUT': 'write',
        'PATCH': 'write',
        'DELETE': 'delete',
    }
    return method_permission_mapping.get(method.upper(), 'read')

def has_permission(user_role: str, resource_name: str, required_permission: str) -> bool:
    """Check if user role has permission for the resource and action"""
    if user_role not in RESOURCES_FOR_ROLES:
        return False
    
    user_permissions = RESOURCES_FOR_ROLES[user_role]
    
    if resource_name in user_permissions:
        return required_permission in user_permissions[resource_name]
    
    parent_resource = resource_name.split('/')[0] if '/' in resource_name else resource_name
    if parent_resource in user_permissions:
        return required_permission in user_permissions[parent_resource]
    
    return False

def require_permission(resource: str = None, permission: str = None):
    """
    Create an RBAC dependency that checks permissions
    
    Args:
        resource: Specific resource name (auto-detected if not provided)
        permission: Specific permission (auto-detected if not provided)
    """
    def check_rbac(request: Request):
        """RBAC dependency function"""
        try:
            current_user = getattr(request.state, 'current_user', None)
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_role = 'user'  # default fallback to match registration default
            if isinstance(current_user, dict) and 'role' in current_user:
                user_role = current_user['role']
            else:
                user_role = getattr(current_user, 'role', 'agent')

            resource_name = resource or normalize_path(str(request.url.path))
            required_permission = permission or translate_method_to_action(request.method)
            
            logger.info(f"RBAC Check - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")

            if not has_permission(user_role, resource_name, required_permission):
                logger.warning(f"Access denied - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. {user_role.title()} role does not have {required_permission} permission for {resource_name}"
                )
            
            logger.info(f"Access granted - User: {user_role}, Resource: {resource_name}, Permission: {required_permission}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"RBAC dependency error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization check failed"
            )
    
    return check_rbac

# Pre-defined RBAC dependencies
require_admin = require_permission("admin", "read")
require_admin_write = require_permission("admin", "write")
require_admin_delete = require_permission("admin", "delete")

require_user_management = require_permission("users", "read")
require_user_management_write = require_permission("users", "write")
require_user_management_delete = require_permission("users", "delete")

require_profile_read = require_permission("users/profiles", "read")
require_profile_write = require_permission("users/profiles", "write")

require_analytics = require_permission("analytics", "read")
require_settings = require_permission("settings", "read")
require_settings_write = require_permission("settings", "write")

require_content_read = require_permission("content", "read")
require_content_write = require_permission("content", "write")
require_content_delete = require_permission("content", "delete")

require_reports = require_permission("reports", "read")
require_reports_write = require_permission("reports", "write")
