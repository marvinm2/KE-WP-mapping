# Architecture Documentation

## KE-WP Mapping Application Architecture

This document provides a comprehensive overview of the application's architecture, design patterns, and technical implementation.

## Table of Contents
- [Overview](#overview)
- [Architecture Patterns](#architecture-patterns)
- [Blueprint Structure](#blueprint-structure)
- [Service Layer](#service-layer)
- [Configuration Management](#configuration-management)
- [Error Handling](#error-handling)
- [Security Architecture](#security-architecture)
- [Database Design](#database-design)
- [API Design](#api-design)
- [Monitoring & Observability](#monitoring--observability)

## Overview

The KE-WP Mapping Application follows modern Flask best practices with a **modular blueprint architecture**. The application was refactored from a monolithic 758-line structure to a clean, maintainable system with clear separation of concerns.

### Key Architectural Principles
- **Single Responsibility**: Each module has a clear, focused purpose
- **Dependency Injection**: Services are injected rather than globally accessed
- **Configuration Management**: Environment-aware settings
- **Error Resilience**: Comprehensive error handling and recovery
- **Security by Design**: Multiple layers of security controls

## Architecture Patterns

### 1. Application Factory Pattern
```python
def create_app(config_name: str = None) -> Flask:
    """Create and configure Flask application instance"""
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize services
    services = ServiceContainer(config)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    return app
```

**Benefits:**
- Flexible application instantiation
- Easy testing with different configurations
- Clean separation of setup logic

### 2. Dependency Injection Pattern
```python
class ServiceContainer:
    """Centralized service management with singleton patterns"""
    
    @property
    def database(self) -> Database:
        if self._database is None:
            self._database = Database(self.config.DATABASE_PATH)
        return self._database
    
    @property
    def mapping_model(self) -> MappingModel:
        if self._mapping_model is None:
            self._mapping_model = MappingModel(self.database)
        return self._mapping_model
```

**Benefits:**
- Testable code through injection
- Singleton pattern for expensive resources
- Clear service dependencies

### 3. Blueprint Pattern
```python
# blueprints/api.py
api_bp = Blueprint('api', __name__)

@api_bp.route('/submit', methods=['POST'])
@submission_rate_limit
@login_required
def submit():
    # API logic here
```

**Benefits:**
- Modular route organization
- Clear separation of concerns
- Easy feature addition/removal

## Blueprint Structure

### File Organization
```
blueprints/
├── __init__.py          # Blueprint exports
├── auth.py              # Authentication & OAuth
├── api.py               # Data API endpoints
├── admin.py             # Admin functionality
└── main.py              # Core application routes
```

### Blueprint Responsibilities

#### **Auth Blueprint** (`auth.py`)
- GitHub OAuth integration
- Login/logout workflows
- Session management
- User authentication

```python
@auth_bp.route('/login')
def login():
    redirect_uri = url_for('auth.authorize', _external=True)
    return github_client.authorize_redirect(redirect_uri)
```

#### **API Blueprint** (`api.py`)
- Data validation and submission
- SPARQL endpoint integration
- Rate limiting and caching
- Proposal management

```python
@api_bp.route('/submit', methods=['POST'])
@submission_rate_limit
@login_required
def submit():
    # Validation, processing, database operations
```

#### **Admin Blueprint** (`admin.py`)
- Proposal review dashboard
- Admin authentication
- Management operations
- Administrative reporting

```python
@admin_bp.route('/proposals')
@admin_required
@monitor_performance
def admin_proposals():
    # Admin-only proposal management
```

#### **Main Blueprint** (`main.py`)
- Core application pages
- Dataset exploration
- Public endpoints
- Template rendering

```python
@main_bp.route('/')
@monitor_performance
def index():
    return render_template('index.html')
```

## Service Layer

### ServiceContainer Design
```python
class ServiceContainer:
    """Dependency injection container"""
    
    def __init__(self, config):
        self.config = config
        self._database = None
        self._models = {}
        self._clients = {}
    
    def get_health_status(self) -> dict:
        """System health monitoring"""
        return {
            'database': self._test_database(),
            'oauth': self._test_oauth(),
            'services': self._test_services()
        }
```

### Service Lifecycle
1. **Lazy Initialization**: Services created on first access
2. **Singleton Pattern**: Single instance per application
3. **Health Monitoring**: Regular service health checks
4. **Graceful Cleanup**: Proper resource cleanup on shutdown

## Configuration Management

### Configuration Classes
```python
class Config:
    """Base configuration"""
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'ke_wp_mapping.db')

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
```

### Environment Variables
| Variable | Purpose | Required |
|----------|---------|----------|
| `FLASK_SECRET_KEY` | Session encryption | Yes |
| `GITHUB_CLIENT_ID` | OAuth authentication | Yes |
| `ADMIN_USERS` | Administrative access | Yes |
| `DATABASE_PATH` | SQLite database location | No |
| `PORT` | Server port | No |

## Error Handling

### Error Handler Architecture
```python
# error_handlers.py
class ApplicationError(Exception):
    """Base application error with status code"""
    
class ValidationError(ApplicationError):
    """Input validation errors (400)"""
    
class AuthenticationError(ApplicationError):
    """Authentication errors (401)"""
```

### Error Flow
1. **Exception Occurs**: In any blueprint or service
2. **Error Handler**: Catches and categorizes error
3. **Response Generation**: JSON or HTML based on request type
4. **Logging**: Error details logged with context
5. **User Response**: Appropriate error message displayed

### Error Response Format
```json
{
  "error": "User-friendly error message",
  "details": {"field": "validation details"},
  "status_code": 400
}
```

## Security Architecture

### Multi-Layer Security
1. **Authentication**: GitHub OAuth 2.0
2. **Authorization**: Role-based access control
3. **Input Validation**: Marshmallow schemas
4. **CSRF Protection**: Token-based protection
5. **Rate Limiting**: Request throttling
6. **Session Security**: Secure cookie configuration

### Security Flow
```
Request → Rate Limit Check → Authentication → Authorization → 
CSRF Validation → Input Validation → Business Logic → Response
```

### Security Headers
```python
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,    # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    WTF_CSRF_TIME_LIMIT=3600        # 1-hour token validity
)
```

## Database Design

### Entity Relationship
```
Users (GitHub OAuth)
    ↓
Mappings (KE-WP relationships)
    ↓
Proposals (Change requests)
    ↓
Cache (SPARQL responses)
```

### Table Schemas

#### Mappings Table
```sql
CREATE TABLE mappings (
    id INTEGER PRIMARY KEY,
    ke_id TEXT NOT NULL,
    ke_title TEXT,
    wp_id TEXT NOT NULL,
    wp_title TEXT,
    connection_type TEXT,
    confidence_level INTEGER,
    created_by TEXT,
    created_at TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP
);
```

#### Proposals Table
```sql
CREATE TABLE proposals (
    id INTEGER PRIMARY KEY,
    mapping_id INTEGER,
    user_name TEXT,
    user_email TEXT,
    github_username TEXT,
    proposed_delete BOOLEAN,
    proposed_confidence INTEGER,
    proposed_connection_type TEXT,
    status TEXT DEFAULT 'pending',
    admin_notes TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (mapping_id) REFERENCES mappings (id)
);
```

## API Design

### RESTful Principles
- **Resource-based URLs**: `/admin/proposals/<id>`
- **HTTP Methods**: GET, POST for appropriate operations
- **Status Codes**: Proper HTTP status code usage
- **Content Types**: JSON for APIs, HTML for pages

### Rate Limiting Strategy
```python
# Different limits for different operations
@sparql_rate_limit      # 30/minute for SPARQL queries
@submission_rate_limit  # 10/minute for submissions
@general_rate_limit     # 100/minute for general use
```

### API Response Format
```python
# Success Response
{
    "message": "Operation completed successfully",
    "data": {...},
    "timestamp": 1754582360
}

# Error Response  
{
    "error": "Validation failed",
    "details": {"field": "error details"},
    "status_code": 400
}
```

## Monitoring & Observability

### Health Check System
```python
@app.route('/health')
def health_check():
    return {
        "status": "healthy|degraded|unhealthy",
        "timestamp": int(time.time()),
        "version": "2.0.0",
        "services": {
            "database": True,
            "oauth": True,
            "services": {...}
        }
    }
```

### Metrics Collection
- **Request Metrics**: Response times, error rates
- **System Metrics**: Memory, CPU usage
- **Business Metrics**: Mapping submissions, user activity
- **Error Metrics**: Error frequency, types

### Logging Strategy
```python
# Structured logging with context
logger.info(f"New mapping created: {ke_id} -> {wp_id} by {username}")
logger.error(f"Database error in {function_name}: {error}", exc_info=True)
logger.warning(f"Rate limit exceeded: {endpoint} from {ip_address}")
```

## Performance Considerations

### Optimization Strategies
1. **Database Indexing**: Key fields for fast lookups
2. **SPARQL Caching**: 24-hour cache for external queries
3. **Lazy Loading**: Services loaded on demand
4. **Connection Pooling**: Efficient database connections
5. **Static Assets**: Proper caching headers

### Scalability Patterns
- **Horizontal Scaling**: Blueprint architecture supports load balancing
- **Database Scaling**: SQLite for development, PostgreSQL for production
- **Caching Layer**: Redis for production environments
- **CDN Integration**: Static asset delivery

## Testing Architecture

### Test Structure
```python
# Application factory enables easy testing
def test_health_endpoint():
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
```

### Test Categories
- **Unit Tests**: Individual function testing
- **Integration Tests**: Blueprint interaction testing
- **Security Tests**: Authentication and authorization
- **Performance Tests**: Load and stress testing

## Deployment Considerations

### Environment Setup
- **Development**: Debug mode, detailed logging
- **Production**: Security headers, optimized settings
- **Testing**: In-memory database, mock services

### Production Recommendations
```python
# Production configuration
class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Use PostgreSQL instead of SQLite
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Use Redis for caching
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL')
```

---

This architecture provides a robust, maintainable foundation for the KE-WP Mapping application, supporting both current functionality and future growth.