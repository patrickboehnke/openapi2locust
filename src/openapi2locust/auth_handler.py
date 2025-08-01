"""Authentication handler module for different auth types."""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class AuthType(Enum):
    """Supported authentication types."""
    API_KEY = "apiKey"
    HTTP_BASIC = "http_basic"
    HTTP_BEARER = "http_bearer"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"


class AuthHandlerError(Exception):
    """Base exception for AuthHandler."""
    pass


class InvalidSecuritySchemeError(AuthHandlerError):
    """Raised when an invalid security scheme is provided."""
    pass


class AuthHandler:
    """Handle different authentication schemes from OpenAPI specs."""
    
    def __init__(self, security_schemes: Optional[Dict[str, Any]] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.security_schemes = self._validate_security_schemes(security_schemes or {})
    
    def get_auth_setup_code(self, security_requirements: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Generate authentication setup code for Locust."""
        if not isinstance(security_requirements, list):
            raise ValueError("security_requirements must be a list")
        
        setup_lines = []
        imports = []
        
        if not security_requirements:
            return "", []
        
        try:
            # Process first security requirement (OR logic between requirements)
            for security_req in security_requirements[:1]:
                if not isinstance(security_req, dict):
                    self.logger.warning(f"Invalid security requirement type: {type(security_req)}")
                    continue
                    
                for scheme_name, scopes in security_req.items():
                    if not self._is_valid_scheme_name(scheme_name):
                        self.logger.warning(f"Invalid scheme name: {scheme_name}")
                        continue
                        
                    scheme = self.security_schemes.get(scheme_name)
                    if scheme:
                        auth_code, auth_imports = self._generate_auth_code(scheme_name, scheme, scopes)
                        if auth_code:
                            setup_lines.append(auth_code)
                            imports.extend(auth_imports)
            
            return "\n        ".join(setup_lines), list(set(imports))
            
        except Exception as e:
            self.logger.error(f"Failed to generate auth setup code: {e}")
            raise AuthHandlerError(f"Auth setup generation failed: {e}") from e
    
    def _generate_auth_code(self, scheme_name: str, scheme: Dict[str, Any], scopes: List[str]) -> Tuple[str, List[str]]:
        """Generate authentication code for a specific scheme."""
        auth_type = scheme.get("type")
        imports = []
        
        if auth_type == "apiKey":
            return self._generate_api_key_auth(scheme_name, scheme)
        elif auth_type == "http":
            return self._generate_http_auth(scheme_name, scheme)
        elif auth_type == "oauth2":
            return self._generate_oauth2_auth(scheme_name, scheme, scopes)
        elif auth_type == "openIdConnect":
            return self._generate_openid_connect_auth(scheme_name, scheme)
        else:
            return "", []
    
    def _generate_api_key_auth(self, scheme_name: str, scheme: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Generate API key authentication code."""
        location = scheme.get("in", "header")
        name = scheme.get("name", "X-API-Key")
        
        if location == "header":
            code = f'self.client.headers["{name}"] = "{{{scheme_name.upper()}_API_KEY}}"'
        elif location == "query":
            code = f'self.{scheme_name}_api_key = "{{{scheme_name.upper()}_API_KEY}}"'
        elif location == "cookie":
            code = f'self.client.cookies["{name}"] = "{{{scheme_name.upper()}_API_KEY}}"'
        else:
            code = f'self.client.headers["{name}"] = "{{{scheme_name.upper()}_API_KEY}}"'
        
        return code, []
    
    def _generate_http_auth(self, scheme_name: str, scheme: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Generate HTTP authentication code."""
        http_scheme = scheme.get("scheme", "basic").lower()
        
        if http_scheme == "basic":
            code = f'''import base64
        username = "{{{scheme_name.upper()}_USERNAME}}"
        password = "{{{scheme_name.upper()}_PASSWORD}}"
        credentials = base64.b64encode(f"{{username}}:{{password}}".encode()).decode()
        self.client.headers["Authorization"] = f"Basic {{credentials}}"'''
            return code, ["base64"]
        elif http_scheme == "bearer":
            code = f'self.client.headers["Authorization"] = f"Bearer {{{scheme_name.upper()}_TOKEN}}"'
            return code, []
        else:
            code = f'self.client.headers["Authorization"] = f"{http_scheme.title()} {{{scheme_name.upper()}_TOKEN}}"'
            return code, []
    
    def _generate_oauth2_auth(self, scheme_name: str, scheme: Dict[str, Any], scopes: List[str]) -> Tuple[str, List[str]]:
        """Generate OAuth2 authentication code."""
        code = f'''# OAuth2 authentication - you'll need to implement token acquisition
        self.client.headers["Authorization"] = f"Bearer {{{scheme_name.upper()}_ACCESS_TOKEN}}"'''
        return code, []
    
    def _generate_openid_connect_auth(self, scheme_name: str, scheme: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Generate OpenID Connect authentication code."""
        code = f'''# OpenID Connect authentication - you'll need to implement token acquisition
        self.client.headers["Authorization"] = f"Bearer {{{scheme_name.upper()}_ID_TOKEN}}"'''
        return code, []
    
    def get_auth_comments(self, security_requirements: List[Dict[str, Any]]) -> List[str]:
        """Generate comments explaining authentication setup."""
        comments = []
        
        if not security_requirements:
            return ["# No authentication required"]
        
        comments.append("# Authentication setup:")
        comments.append("# Set the following environment variables:")
        
        for security_req in security_requirements[:1]:
            for scheme_name, scopes in security_req.items():
                scheme = self.security_schemes.get(scheme_name)
                if scheme:
                    auth_comments = self._get_scheme_comments(scheme_name, scheme)
                    comments.extend(auth_comments)
        
        return comments
    
    def _get_scheme_comments(self, scheme_name: str, scheme: Dict[str, Any]) -> List[str]:
        """Get comments for a specific authentication scheme."""
        auth_type = scheme.get("type")
        comments = []
        
        if auth_type == "apiKey":
            comments.append(f"# - {scheme_name.upper()}_API_KEY=your_api_key_here")
        elif auth_type == "http":
            http_scheme = scheme.get("scheme", "basic").lower()
            if http_scheme == "basic":
                comments.extend([
                    f"# - {scheme_name.upper()}_USERNAME=your_username",
                    f"# - {scheme_name.upper()}_PASSWORD=your_password"
                ])
            else:
                comments.append(f"# - {scheme_name.upper()}_TOKEN=your_token_here")
        elif auth_type == "oauth2":
            comments.append(f"# - {scheme_name.upper()}_ACCESS_TOKEN=your_oauth2_access_token")
        elif auth_type == "openIdConnect":
            comments.append(f"# - {scheme_name.upper()}_ID_TOKEN=your_openid_token")
        
        return comments
    
    def get_request_auth_params(self, security_requirements: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get request-specific authentication parameters."""
        if not isinstance(security_requirements, list):
            raise ValueError("security_requirements must be a list")
            
        params = {}
        
        if not security_requirements:
            return params
        
        try:
            for security_req in security_requirements[:1]:
                if not isinstance(security_req, dict):
                    continue
                    
                for scheme_name, scopes in security_req.items():
                    if not self._is_valid_scheme_name(scheme_name):
                        continue
                        
                    scheme = self.security_schemes.get(scheme_name)
                    if scheme and scheme.get("type") == "apiKey" and scheme.get("in") == "query":
                        name = self._sanitize_parameter_name(scheme.get("name", "api_key"))
                        if name:
                            params[name] = f"self.{self._sanitize_variable_name(scheme_name)}_api_key"
            
            return params
            
        except Exception as e:
            self.logger.error(f"Failed to get request auth params: {e}")
            return {}
    
    def _validate_security_schemes(self, security_schemes: Dict[str, Any]) -> Dict[str, Any]:
        """Validate security schemes input."""
        if not isinstance(security_schemes, dict):
            raise InvalidSecuritySchemeError("security_schemes must be a dictionary")
        
        validated_schemes = {}
        for scheme_name, scheme in security_schemes.items():
            if not isinstance(scheme_name, str) or not scheme_name.strip():
                self.logger.warning(f"Invalid scheme name: {scheme_name}")
                continue
            
            # Validate scheme name format for security
            if not self._is_valid_scheme_name(scheme_name):
                self.logger.warning(f"Invalid scheme name format: {scheme_name}")
                continue
                
            if not isinstance(scheme, dict):
                self.logger.warning(f"Invalid scheme data for {scheme_name}: {type(scheme)}")
                continue
                
            if "type" not in scheme:
                self.logger.warning(f"Missing type in scheme {scheme_name}")
                continue
                
            validated_schemes[scheme_name] = scheme
            
        return validated_schemes
    
    def _is_valid_scheme_name(self, scheme_name: str) -> bool:
        """Validate scheme name."""
        if not isinstance(scheme_name, str):
            return False
        # Allow alphanumeric and underscore, reasonable length
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]{0,49}$', scheme_name))
    
    def _sanitize_parameter_name(self, name: str) -> str:
        """Sanitize parameter name for header/query usage."""
        if not isinstance(name, str) or not name.strip():
            return ""
        # Remove control characters and limit length
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name.strip())
        return sanitized[:100] if sanitized else ""
    
    def _sanitize_variable_name(self, name: str) -> str:
        """Sanitize variable name for Python usage."""
        if not isinstance(name, str) or not name.strip():
            return "auth"
        # Convert to valid Python variable name
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
        if not sanitized[0].isalpha():
            sanitized = 'auth_' + sanitized
        return sanitized[:50]