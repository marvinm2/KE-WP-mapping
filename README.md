# KE-WP Mapping Application

[![CI/CD Pipeline](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/ci.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/ci.yml)
[![Docker Build & Test](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/docker.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/docker.yml)
[![Code Quality](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/code-quality.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/code-quality.yml)
[![Security & Compliance](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/security.yml/badge.svg)](https://github.com/marvinm2/KE-WP-mapping/actions/workflows/security.yml)

A modern Flask-based web application for mapping Key Events (KEs) to WikiPathways (WPs) and Gene Ontology Biological Process (GO BP) terms with comprehensive metadata management. Built with a modular blueprint architecture for enhanced maintainability and scalability.

## Features

### Core Functionality

- **KE-WP Mapping**: Create relationships between Key Events and WikiPathways with connection types and confidence levels
- **KE-GO Mapping**: Map Key Events to Gene Ontology Biological Process (BP) terms with gene-based and semantic scoring
- **Intelligent Pathway Suggestions**: Advanced algorithm suggesting relevant pathways based on Key Events using:
  - Multi-algorithm text similarity with biological term weighting
  - Gene-based pathway matching with overlap analysis
  - BioBERT semantic similarity with pre-computed embeddings
  - Dynamic confidence scoring with non-linear scaling
- **GO Term Suggestions**: Intelligent GO BP term recommendations using:
  - Pre-computed BioBERT embeddings for ~30K GO BP terms
  - Gene annotation overlap between KE-associated genes and GO terms
  - Hybrid scoring combining gene, text, and semantic signals
- **Streamlined Confidence Assessment**: 4-question guided workflow with biological level weighting:
  - Transparent scoring algorithm (0-7.5 points) with biological level bonus
  - Automatic +1 bonus for molecular/cellular/tissue-level Key Events
  - Progressive question disclosure with collapsible answered steps
  - KE + Pathway info cards displayed alongside each assessment
  - Edit previous answers with automatic recalculation of subsequent steps
  - Real-time score calculation and detailed feedback
- **Data Exploration**: Interactive, searchable dataset browser with advanced filtering
- **Proposal System**: Community-driven change proposals with admin review workflow
- **Real-time SPARQL Integration**: Live data from AOP-Wiki and WikiPathways endpoints
- **Export Capabilities**: Download datasets in multiple formats

### User Experience Enhancements

- **Unified Pathway Discovery**: Step 2 organizes pathway selection into three sub-tabs:
  - **Suggested**: AI-powered pathway recommendations based on selected Key Event
  - **Search**: Full-text pathway search with fuzzy matching
  - **Browse All**: Traditional dropdown with pathway descriptions, SVG previews, and collapsible text
- **KE Context Panel**: When a Key Event is selected, an expandable panel shows:
  - AOP membership with direct links to AOP-Wiki
  - Existing WP and GO mappings with confidence levels
  - Summary badges for quick overview
- **Pathway Previews**: Inline pathway information with SVG figure previews and click-to-expand
- **Data Provenance**: Version information display for data sources (AOP-Wiki, WikiPathways) in application footer
- **Responsive Design**: Mobile-friendly layouts with responsive grid for info cards and assessment panels

### Security & Authentication

- **GitHub OAuth Integration**: Secure authentication with GitHub
- **Role-based Access Control**: Admin dashboard for proposal management with proper Docker deployment support
- **CSRF Protection**: Comprehensive security against cross-site attacks
- **Rate Limiting**: API protection with intelligent throttling

### Architecture

- **Blueprint Modular Design**: Clean separation of concerns
- **Dependency Injection**: Testable and maintainable code structure
- **Configuration Management**: Environment-aware settings with Docker support
- **Health Monitoring**: System status and performance metrics
- **Centralized Error Handling**: Robust error management
- **Database Migrations**: Automatic schema updates with admin field support

## CI/CD & Quality Assurance

This project includes comprehensive GitHub Actions workflows for automated testing, quality assurance, and deployment:

### CI/CD Pipeline

- **Matrix Testing**: Python 3.10 & 3.11 compatibility
- **Automated Testing**: Full test suite with pytest and coverage reporting
- **Code Formatting**: Black code formatting and isort import sorting
- **Environment Testing**: Validates application startup and health endpoints

### Docker Build & Test

- **Multi-platform Builds**: AMD64 and ARM64 architecture support
- **Container Testing**: Automated health checks and endpoint validation
- **Docker Compose Testing**: Full stack deployment validation
- **Production Ready**: Optimized containers with proper security practices

### Code Quality
- **Linting**: Flake8, Black, isort, MyPy, and Pylint validation
- **Security Analysis**: Bandit, Safety, and Semgrep security scanning
- **Complexity Analysis**: Code complexity monitoring with Radon
- **Documentation**: Style checking and coverage validation

### Security & Compliance
- **SAST**: Static Application Security Testing with multiple tools
- **Dependency Scanning**: Automated vulnerability detection
- **Container Security**: Trivy container image scanning
- **License Compliance**: Automated license checking and SBOM generation

All workflows run automatically on push to main branch and can be triggered manually for testing.

## Quick Start

### Prerequisites
- Python 3.10 or 3.11
- Git
- GitHub account (for OAuth)

> **Note:** The initial clone is ~170 MB due to pre-computed embedding files.

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/marvinm2/KE-WP-mapping.git
   cd KE-WP-mapping
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / macOS
   # venv\Scripts\activate    # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   This installs PyTorch and sentence-transformers (~2 GB download on first install).

4. **Set up GitHub OAuth App:**
   - Go to [GitHub Developer Settings](https://github.com/settings/developers)
   - Create new OAuth App with:
     - **Application name**: `KE-WP Mapping Tool`
     - **Homepage URL**: `http://localhost:5000`
     - **Authorization callback URL**: `http://localhost:5000/callback`
   - Copy Client ID and Client Secret

5. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Open `.env` in a text editor and fill in each value:

   | Variable | How to get it |
   |----------|---------------|
   | `FLASK_SECRET_KEY` | Run `python -c "import secrets; print(secrets.token_hex(32))"` and paste the output |
   | `GITHUB_CLIENT_ID` | Copy the **Client ID** from the OAuth App you created in step 4 |
   | `GITHUB_CLIENT_SECRET` | Click **Generate a new client secret** in the OAuth App and copy it |
   | `ADMIN_USERS` | Your GitHub username (comma-separated for multiple admins, e.g. `alice,bob`) |

   Example `.env` (do **not** use these values):
   ```env
   FLASK_SECRET_KEY=a3f1b9c7e8d24...   # generated hex string
   GITHUB_CLIENT_ID=Iv1.abc123def456
   GITHUB_CLIENT_SECRET=0123456789abcdef...
   ADMIN_USERS=your-github-username
   PORT=5000
   ```

   Optional variables (defaults are fine for local development):
   ```env
   FLASK_ENV=development          # or "production"
   FLASK_DEBUG=true                # set to "false" in production
   DATABASE_PATH=ke_wp_mapping.db  # path to SQLite database
   HOST=127.0.0.1                  # bind address
   RATELIMIT_STORAGE_URL=memory:// # rate-limit backend
   ```

6. **Launch the application:**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
   Or run directly with `python app.py`.

7. **Access the application:**
   - Open: http://localhost:5000
   - Click "Login with GitHub"
   - Start mapping KE-WP relationships!

### Run with Docker

```bash
docker pull ghcr.io/marvinm2/ke-wp-mapping:latest
docker run -d -p 5000:5000 \
  -e FLASK_SECRET_KEY=your-secret-key \
  -e GITHUB_CLIENT_ID=your-client-id \
  -e GITHUB_CLIENT_SECRET=your-client-secret \
  -e ADMIN_USERS=your-github-username \
  ghcr.io/marvinm2/ke-wp-mapping:latest
```

Or with Docker Compose (clone repo first):
```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

## Architecture Overview

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
├── rate_limiter.py           # API rate limiting
├── pathway_suggestions.py    # Intelligent pathway suggestions
├── go_suggestions.py         # GO term suggestion service
├── ke_gene_service.py        # Gene extraction from Key Events
└── scoring_utils.py          # Shared scoring utilities
```

### Key Components
- **Application Factory**: Creates configured Flask instances
- **Service Container**: Manages dependencies with singleton patterns
- **Blueprint System**: Modular route organization by functionality
- **Configuration Classes**: Environment-specific settings (dev/prod/test)
- **Error Handlers**: Consistent error responses across all endpoints

## API Documentation

### Page Routes

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/` | GET | Main application page | Optional |
| `/explore` | GET | Dataset exploration interface | Optional |
| `/download` | GET | Dataset download page | Optional |
| `/ke-details` | GET | Key Event detail page | Optional |
| `/pw-details` | GET | Pathway detail page | Optional |
| `/documentation` | GET | Application documentation | Optional |
| `/login` | GET | GitHub OAuth login | None |
| `/logout` | GET | User logout | Required |

### API Endpoints

| Endpoint | Method | Description | Rate Limit |
|----------|--------|-------------|------------|
| `/check` | POST | Validate KE-WP pair existence | General |
| `/submit` | POST | Create new KE-WP mapping | Submission |
| `/get_ke_options` | GET | Fetch Key Event options | SPARQL |
| `/get_pathway_options` | GET | Fetch pathway options | SPARQL |
| `/get_aop_options` | GET | Fetch AOP options | SPARQL |
| `/get_aop_kes/<aop_id>` | GET | Fetch Key Events for a specific AOP | SPARQL |
| `/get_data_versions` | GET | Fetch data source version info | SPARQL |
| `/suggest_pathways/<ke_id>` | GET | Pathway suggestions for a Key Event | SPARQL |
| `/search_pathways` | GET | Full-text pathway search with fuzzy matching | SPARQL |
| `/ke_genes/<ke_id>` | GET | Genes associated with a Key Event | SPARQL |
| `/api/ke_context/<ke_id>` | GET | KE context: AOPs, existing WP/GO mappings | General |
| `/api/scoring-config` | GET | KE-WP assessment scoring configuration | General |
| `/suggest_go_terms/<ke_id>` | GET | GO BP term suggestions for a Key Event | SPARQL |
| `/submit_go_mapping` | POST | Create new KE-GO mapping | Submission |
| `/check_go_entry` | POST | Check if KE-GO pair exists | General |
| `/api/go-scoring-config` | GET | KE-GO assessment scoring configuration | General |
| `/submit_proposal` | POST | Submit change proposal | Submission |

### Admin Endpoints

| Endpoint | Method | Description | Access |
|----------|--------|-------------|---------|
| `/admin/proposals` | GET | Proposal management dashboard | Admin only |
| `/admin/proposals/<id>` | GET | View proposal details | Admin only |
| `/admin/proposals/<id>/approve` | POST | Approve proposal | Admin only |
| `/admin/proposals/<id>/reject` | POST | Reject proposal | Admin only |

### Export & Data Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/export/<format>` | GET | Export dataset (csv, tsv, json, excel, rdf) |
| `/export/formats` | GET | List available export formats |
| `/dataset/metadata` | GET | Dataset metadata |
| `/dataset/versions` | GET | Dataset version history |
| `/dataset/citation` | GET | Citation information |

### Monitoring Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health status |
| `/metrics` | GET | Application metrics |
| `/metrics/<endpoint>` | GET | Endpoint-specific stats |

## Security Features

- **OAuth 2.0**: Secure GitHub authentication
- **CSRF Protection**: All forms protected with tokens
- **Input Validation**: Marshmallow schema validation
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Input sanitization and escaping
- **Rate Limiting**: Configurable request throttling
- **Session Security**: HTTPOnly, Secure, SameSite cookies

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Flask session encryption key | - | Yes |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | - | Yes |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret | - | Yes |
| `ADMIN_USERS` | Comma-separated admin usernames | - | Yes |
| `FLASK_ENV` | Environment mode | `development` | No |
| `FLASK_DEBUG` | Debug mode toggle | `true` | No |
| `PORT` | Server port | `5000` | No |
| `DATABASE_PATH` | SQLite database path | `ke_wp_mapping.db` | No |
| `RATELIMIT_STORAGE_URL` | Rate limiting backend | `memory://` | No |

### Configuration Classes

- **DevelopmentConfig**: Local development settings
- **ProductionConfig**: Production-ready configuration
- **TestingConfig**: Unit testing environment

## Testing

```bash
# Run the full test suite
PYTHONPATH=. pytest tests/ -v

# Run with test configuration
python -c "from app import create_app; app = create_app('testing')"

# Test specific endpoints
curl http://localhost:5000/health
curl http://localhost:5000/metrics
```

## Monitoring & Health Checks

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

## Development

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

## Troubleshooting

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

## Data Sources

- **Key Events**: [AOP-Wiki SPARQL Endpoint](https://aopwiki.rdf.bigcat-bioinformatics.org/sparql)
- **WikiPathways**: [WikiPathways SPARQL Endpoint](https://sparql.wikipathways.org/sparql)
- **Gene Ontology**: [GO OBO file](http://purl.obolibrary.org/obo/go.obo) (Biological Process terms)
- **GO Annotations**: [UniProt-GOA Human](https://www.ebi.ac.uk/GOA) (GO-gene associations)
- **Caching**: 24-hour cache for SPARQL responses

## Contributing

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

## Support

- **Issues**: [GitHub Issues](https://github.com/marvinm2/KE-WP-mapping/issues)
- **Documentation**: This README and inline code documentation
- **Contact**: [marvin.martens@maastrichtuniversity.nl]

## License

This project is licensed under the GPL-2.0 License - see the LICENSE file for details.

## Acknowledgments

- **AOP-Wiki**: Key Event data and SPARQL endpoint
- **WikiPathways**: Pathway data and SPARQL integration
- **Gene Ontology Consortium**: GO term ontology and annotations
- **UniProt-GOA**: Gene Ontology annotation database
- **BiGCaT**: Bioinformatics research group at Maastricht University
- **Flask Community**: Framework and extension ecosystem

---

**Built with modern Flask best practices and blueprint architecture for maintainable, scalable bioinformatics applications.**
