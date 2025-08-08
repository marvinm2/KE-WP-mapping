# KE-WP Mapping Application 🧬

[![CI/CD Pipeline](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/ci.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/ci.yml)
[![Docker Build & Test](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/docker.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/docker.yml)
[![Code Quality](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/code-quality.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/code-quality.yml)
[![Security & Compliance](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/security.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/security.yml)

A modern Flask-based web application for mapping Key Events (KEs) to WikiPathways (WPs) with comprehensive metadata management. Built with a modular blueprint architecture for enhanced maintainability and scalability.

## 🌟 Features

### Core Functionality
- **🔗 KE-WP Mapping**: Create relationships between Key Events and WikiPathways with connection types and confidence levels
- **🔍 Data Exploration**: Interactive, searchable dataset browser with advanced filtering
- **📝 Proposal System**: Community-driven change proposals with admin review workflow
- **📊 Real-time SPARQL Integration**: Live data from AOP-Wiki and WikiPathways endpoints
- **💾 Export Capabilities**: Download datasets in multiple formats

### Security & Authentication
- **🔐 GitHub OAuth Integration**: Secure authentication with GitHub
- **👥 Role-based Access Control**: Admin dashboard for proposal management
- **🛡️ CSRF Protection**: Comprehensive security against cross-site attacks
- **🚦 Rate Limiting**: API protection with intelligent throttling

### Architecture
- **🏗️ Blueprint Modular Design**: Clean separation of concerns
- **⚙️ Dependency Injection**: Testable and maintainable code structure
- **🔧 Configuration Management**: Environment-aware settings
- **📈 Health Monitoring**: System status and performance metrics
- **🚨 Centralized Error Handling**: Robust error management

## 🔧 CI/CD & Quality Assurance

This project includes comprehensive GitHub Actions workflows for automated testing, quality assurance, and deployment:

### 🔄 **CI/CD Pipeline**
- **Matrix Testing**: Python 3.10 & 3.11 compatibility
- **Automated Testing**: Full test suite with pytest and coverage reporting
- **Code Formatting**: Black code formatting and isort import sorting
- **Environment Testing**: Validates application startup and health endpoints

### 🐳 **Docker Build & Test**
- **Multi-platform Builds**: AMD64 and ARM64 architecture support
- **Container Testing**: Automated health checks and endpoint validation
- **Docker Compose Testing**: Full stack deployment validation
- **Production Ready**: Optimized containers with proper security practices

### 🔍 **Code Quality**
- **Linting**: Flake8, Black, isort, MyPy, and Pylint validation
- **Security Analysis**: Bandit, Safety, and Semgrep security scanning
- **Complexity Analysis**: Code complexity monitoring with Radon
- **Documentation**: Style checking and coverage validation

### 🛡️ **Security & Compliance**
- **SAST**: Static Application Security Testing with multiple tools
- **Dependency Scanning**: Automated vulnerability detection
- **Container Security**: Trivy container image scanning
- **License Compliance**: Automated license checking and SBOM generation

All workflows run automatically on push to main branch and can be triggered manually for testing.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Git
- GitHub account (for OAuth)

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd KE-WP-mapping
   ```

2. **Set up GitHub OAuth App:**
   - Go to [GitHub Developer Settings](https://github.com/settings/developers)
   - Create new OAuth App with:
     - **Application name**: `KE-WP Mapping Tool`
     - **Homepage URL**: `http://localhost:5000`
     - **Authorization callback URL**: `http://localhost:5000/callback`
   - Copy Client ID and Client Secret

3. **Configure environment:**
   ```bash
   cp .env.template .env
   # Edit .env with your GitHub OAuth credentials
   ```

   Required `.env` configuration:
   ```env
   FLASK_SECRET_KEY=your-unique-secret-key
   GITHUB_CLIENT_ID=your-github-client-id  
   GITHUB_CLIENT_SECRET=your-github-client-secret
   ADMIN_USERS=your-github-username
   PORT=5000
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Launch the application:**
   ```bash
   ./start.sh
   ```

6. **Access the application:**
   - Open: http://localhost:5000
   - Click "Login with GitHub"
   - Start mapping KE-WP relationships!

## 🏗️ Architecture Overview

### Blueprint Structure
```
├── app.py                    # Application factory (147 lines)
├── config.py                 # Environment-aware configuration
├── services.py               # Dependency injection container
├── error_handlers.py         # Centralized error handling
├── blueprints/               # Modular route organization
│   ├── auth.py              # Authentication & OAuth
│   ├── api.py               # Data API endpoints
│   ├── admin.py             # Admin dashboard
│   └── main.py              # Core application routes
├── models.py                 # Data models & database layer
├── schemas.py                # Input validation schemas
├── monitoring.py             # Performance & health monitoring
└── rate_limiter.py           # API rate limiting
```

### Key Components
- **Application Factory**: Creates configured Flask instances
- **Service Container**: Manages dependencies with singleton patterns
- **Blueprint System**: Modular route organization by functionality
- **Configuration Classes**: Environment-specific settings (dev/prod/test)
- **Error Handlers**: Consistent error responses across all endpoints

## 📚 API Documentation

### Core Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/` | GET | Main application page | Optional |
| `/explore` | GET | Dataset exploration interface | Optional |
| `/login` | GET | GitHub OAuth login | None |
| `/logout` | GET | User logout | Required |

### API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/check` | POST | Validate KE-WP pair existence | General |
| `/submit` | POST | Create new mapping | Submission |
| `/get_ke_options` | GET | Fetch Key Events from SPARQL | SPARQL |
| `/get_pathway_options` | GET | Fetch pathways from SPARQL | SPARQL |
| `/submit_proposal` | POST | Submit change proposal | Submission |

### Admin Endpoints

| Endpoint | Method | Description | Access |
|----------|--------|-------------|---------|
| `/admin/proposals` | GET | Proposal management dashboard | Admin only |
| `/admin/proposals/<id>` | GET | View proposal details | Admin only |
| `/admin/proposals/<id>/approve` | POST | Approve proposal | Admin only |
| `/admin/proposals/<id>/reject` | POST | Reject proposal | Admin only |

### Monitoring Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health status |
| `/metrics` | GET | Application metrics |
| `/metrics/<endpoint>` | GET | Endpoint-specific stats |

## 🛡️ Security Features

- **OAuth 2.0**: Secure GitHub authentication
- **CSRF Protection**: All forms protected with tokens
- **Input Validation**: Marshmallow schema validation
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Input sanitization and escaping
- **Rate Limiting**: Configurable request throttling
- **Session Security**: HTTPOnly, Secure, SameSite cookies

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Flask session encryption key | - | ✅ |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | - | ✅ |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret | - | ✅ |
| `ADMIN_USERS` | Comma-separated admin usernames | - | ✅ |
| `FLASK_ENV` | Environment mode | `development` | ❌ |
| `FLASK_DEBUG` | Debug mode toggle | `true` | ❌ |
| `PORT` | Server port | `5000` | ❌ |
| `DATABASE_PATH` | SQLite database path | `ke_wp_mapping.db` | ❌ |
| `RATELIMIT_STORAGE_URL` | Rate limiting backend | `memory://` | ❌ |

### Configuration Classes
- **DevelopmentConfig**: Local development settings
- **ProductionConfig**: Production-ready configuration
- **TestingConfig**: Unit testing environment

## 🧪 Testing

```bash
# Run with test configuration
python -c "from app import create_app; app = create_app('testing')"

# Test specific endpoints
curl http://localhost:5000/health
curl http://localhost:5000/metrics
```

## 📈 Monitoring & Health Checks

### Health Check Response
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": 1754582360,
  "version": "2.0.0",
  "services": {
    "database": true,
    "oauth": true,
    "services": {
      "mapping_model": true,
      "proposal_model": true,
      "cache_model": true,
      "metrics_collector": false,
      "rate_limiter": false
    }
  }
}
```

### Metrics Available
- System resource usage
- Endpoint response times
- Request/error rates
- Database performance
- Cache hit ratios

## 🔧 Development

### Local Development
```bash
# Enable debug mode
export FLASK_DEBUG=true
export FLASK_ENV=development

# Start with auto-reload
python app.py
```

### Adding New Features
1. Create new blueprint in `blueprints/`
2. Register in `app.py`
3. Add configuration in `config.py`
4. Update service container if needed
5. Add error handling
6. Write tests

## 🐛 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Change port in .env
PORT=5001
# Update GitHub OAuth callback URL accordingly
```

**OAuth not working:**
- Verify callback URL: `http://localhost:5000/callback`
- Check Client ID/Secret in GitHub settings
- Ensure OAuth app is not suspended

**Database errors:**
```bash
# Reset database
rm ke_wp_mapping.db
python app.py  # Will recreate automatically
```

**Permission errors:**
```bash
# Make startup script executable
chmod +x start.sh
```

## 📊 Data Sources

- **Key Events**: [AOP-Wiki SPARQL Endpoint](https://aopwiki.rdf.bigcat-bioinformatics.org/sparql)
- **WikiPathways**: [WikiPathways SPARQL Endpoint](https://sparql.wikipathways.org/sparql)
- **Caching**: 24-hour cache for SPARQL responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the blueprint architecture
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints where applicable
- Add docstrings for all functions/classes
- Maintain separation of concerns with blueprints

## 📋 Changelog

### Version 2.0.0 (Current)
- ✅ **Blueprint Architecture**: Modular application design
- ✅ **Dependency Injection**: Service container pattern
- ✅ **Configuration Management**: Environment-aware settings
- ✅ **Centralized Error Handling**: Consistent error responses
- ✅ **Health Monitoring**: System status endpoints
- ✅ **Enhanced Security**: CSRF protection, input validation

### Version 1.0.0 (Legacy)
- Basic Flask application (758 lines monolithic structure)
- GitHub OAuth authentication
- KE-WP mapping functionality
- Admin proposal system

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: This README and inline code documentation
- **Contact**: [marvin.martens@maastrichtuniversity.nl]

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **AOP-Wiki**: Key Event data and SPARQL endpoint
- **WikiPathways**: Pathway data and SPARQL integration  
- **BiGCaT**: Bioinformatics research group at Maastricht University
- **Flask Community**: Framework and extension ecosystem

---

**🏆 Built with modern Flask best practices and blueprint architecture for maintainable, scalable bioinformatics applications.**