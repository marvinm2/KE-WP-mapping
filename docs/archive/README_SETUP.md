# KE-WP Mapping Application - Setup Guide

## Quick Start with GitHub Login

This guide will get you up and running with the KE-WP Mapping Application in minutes.

### Prerequisites
- Python 3.8+ installed
- Git installed
- GitHub account
- Web browser

### 1. Set Up GitHub OAuth Application

1. **Go to GitHub Developer Settings:**
   - Visit: [https://github.com/settings/developers](https://github.com/settings/developers)
   - Click **"OAuth Apps"** in the left sidebar

2. **Create New OAuth App:**
   - Click **"New OAuth App"**
   - Fill in the application details:
     - **Application name**: `KE-WP Mapping Tool`
     - **Homepage URL**: `http://localhost:5000`
     - **Application description**: `Bioinformatics tool for mapping Key Events to WikiPathways`
     - **Authorization callback URL**: `http://localhost:5000/callback`
   - Click **"Register application"**

3. **Get Your Credentials:**
   - Copy the **Client ID** (starts with `Ov23...`)
   - Click **"Generate a new client secret"**
   - Copy the **Client Secret** (long alphanumeric string)
   - **Important**: Keep these credentials secure!

### 2. Configure the Application

1. **Clone and Navigate:**
   ```bash
   git clone <repository-url>
   cd KE-WP-mapping
   ```

2. **Set Up Environment File:**
   ```bash
   # Copy the template
   cp .env.template .env
   
   # Edit with your favorite editor
   nano .env
   # or
   code .env
   # or
   vim .env
   ```

3. **Fill in Your Credentials:**
   ```env
   # Flask Configuration
   FLASK_SECRET_KEY=your-unique-secret-key-change-this
   FLASK_ENV=development
   FLASK_DEBUG=true
   PORT=5000
   HOST=127.0.0.1

   # GitHub OAuth Configuration (from step 1)
   GITHUB_CLIENT_ID=Ov23liKSETcmWNZMcG5m
   GITHUB_CLIENT_SECRET=your-github-client-secret-here

   # Database Configuration
   DATABASE_PATH=ke_wp_mapping.db

   # Admin Users (your GitHub username)
   ADMIN_USERS=your-github-username

   # Rate Limiting Configuration
   RATELIMIT_STORAGE_URL=memory://
   ```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Make startup script executable
chmod +x start.sh
```

### 4. Launch the Application

**Option A - Using the startup script (Recommended):**
```bash
./start.sh
```

**Option B - Direct Python execution:**
```bash
python app.py
```

You should see output like:
```
KE-WP Mapping Application Startup
=====================================
Configuration loaded
Starting server on http://localhost:5000
GitHub OAuth configured
👤 Admin users: your-username

📝 Press CTRL+C to stop

 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### 5. Access and Use the Application

1. **Open in Browser:**
   - Navigate to: http://localhost:5000
   - You should see the KE-WP Mapping homepage

2. **Login with GitHub:**
   - Click **"Login with GitHub"**
   - You'll be redirected to GitHub
   - Click **"Authorize [your-app-name]"**
   - You'll be redirected back to the application

3. **Start Using the Tool:**
   - **Map KE-WP relationships**: Submit new mappings
   - **Explore dataset**: Browse existing mappings
   - **Access admin features**: Visit `/admin/proposals` (if you're an admin)

## Advanced Configuration

### Environment Variables Reference

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Session encryption key | `a1b2c3d4e5f6...` | Yes |
| `GITHUB_CLIENT_ID` | OAuth client identifier | `Ov23liKSETcm...` | Yes |
| `GITHUB_CLIENT_SECRET` | OAuth client secret | `62a43f428bc7...` | Yes |
| `ADMIN_USERS` | Admin GitHub usernames | `user1,user2,user3` | Yes |
| `FLASK_ENV` | Environment mode | `development`/`production` | No |
| `FLASK_DEBUG` | Enable debug mode | `true`/`false` | No |
| `PORT` | Server port | `5000` | No |
| `HOST` | Server host | `127.0.0.1` | No |
| `DATABASE_PATH` | SQLite database file | `ke_wp_mapping.db` | No |
| `RATELIMIT_STORAGE_URL` | Rate limit storage | `memory://` | No |

### Production Configuration

For production deployment, update your `.env`:
```env
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_SECRET_KEY=very-long-random-secure-key
PORT=80
HOST=0.0.0.0
# Update GitHub OAuth URLs to your domain
```

And update your GitHub OAuth app settings:
- **Homepage URL**: `https://yourdomain.com`
- **Authorization callback URL**: `https://yourdomain.com/callback`

## 🏗️ Architecture Overview

The application uses a modern **Blueprint Architecture**:

```
KE-WP-mapping/
├── app.py                    # Application factory (147 lines)
├── config.py                 # Environment-aware configuration
├── services.py               # Dependency injection container
├── error_handlers.py         # Centralized error handling
├── blueprints/               # Modular route organization
│   ├── auth.py              # GitHub OAuth authentication
│   ├── api.py               # Data API endpoints
│   ├── admin.py             # Admin dashboard
│   └── main.py              # Core application routes
├── models.py                 # Database models
├── monitoring.py             # Performance monitoring
├── rate_limiter.py          # API rate limiting
├── schemas.py               # Input validation
└── templates/               # HTML templates
```

### Key Architectural Benefits:
- **Modular Design**: Easy to maintain and extend
- **Dependency Injection**: Testable and flexible
- **Environment Aware**: Different configs for dev/prod
- **Security First**: Multiple layers of protection
- **Health Monitoring**: Built-in system monitoring

## Security Features

- **OAuth 2.0**: Secure GitHub authentication
- **CSRF Protection**: Cross-site request forgery prevention
- **Input Validation**: Marshmallow schema validation
- **Rate Limiting**: API request throttling
- **Role-based Access**: Admin vs. user permissions
- **Session Security**: Secure cookie configuration

## Available Endpoints

### User Endpoints
- `/` - Main application page
- `/explore` - Dataset exploration
- `/login` - GitHub OAuth login
- `/logout` - User logout

### API Endpoints
- `/check` - Validate KE-WP pair
- `/submit` - Submit new mapping
- `/get_ke_options` - Fetch Key Events
- `/get_pathway_options` - Fetch pathways
- `/submit_proposal` - Submit change proposal

### Admin Endpoints (Admin users only)
- `/admin/proposals` - Proposal management
- `/admin/proposals/<id>/approve` - Approve proposal
- `/admin/proposals/<id>/reject` - Reject proposal

### System Endpoints
- `/health` - System health check
- `/metrics` - Application metrics

## Troubleshooting

### Common Issues and Solutions

**Port already in use:**
```bash
# Change port in .env file
PORT=5001
# Update GitHub OAuth callback URL to match
```

**OAuth authentication not working:**
- Check callback URL matches exactly: `http://localhost:5000/callback`
- Verify Client ID and Secret are correct in `.env`
- Ensure OAuth app is active (not suspended)
- Check for typos in environment variables

**Database errors:**
```bash
# Reset database
rm ke_wp_mapping.db
python app.py  # Database will be recreated
```

**Permission errors:**
```bash
# Make startup script executable
chmod +x start.sh
```

**Missing dependencies:**
```bash
# Install/update dependencies
pip install -r requirements.txt
```

**Configuration validation errors:**
- Check all required variables are set in `.env`
- Ensure no extra spaces around variable names
- Verify GitHub credentials are valid

### Health Check

Test if the application is working:
```bash
# Check application health
curl http://localhost:5000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": 1754582360,
  "version": "2.0.0",
  "services": {
    "database": true,
    "oauth": true,
    "services": {...}
  }
}
```

## 📞 Getting Help

### Support Channels
- **Documentation**: This guide and the main [README.md](README.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md) for version history
- **Issues**: GitHub Issues for bug reports and feature requests
- **Email**: [marvin.martens@maastrichtuniversity.nl]

### Before Requesting Help
1. Check this troubleshooting section
2. Verify your `.env` configuration
3. Test the health endpoint
4. Check the console output for error messages
5. Review recent changes to your setup

---

**You're all set! The KE-WP Mapping Application should now be running with full GitHub OAuth integration.**