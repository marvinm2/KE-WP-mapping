# Deployment Guide

This guide covers deploying the KE-WP Mapping Application to various environments and platforms.

## Table of Contents
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)
- [Monitoring in Production](#monitoring-in-production)

## Production Deployment

### Prerequisites
- Python 3.8+ on production server
- SSL certificate for HTTPS
- Domain name configured
- Production database (PostgreSQL recommended)
- Redis for caching (optional but recommended)

### 1. Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx supervisor

# Install PostgreSQL (if using)
sudo apt install postgresql postgresql-contrib
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository-url> /var/www/ke-wp-mapping
cd /var/www/ke-wp-mapping

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production WSGI server
pip install gunicorn
```

### 3. Production Configuration

Create production environment file:
```bash
# /var/www/ke-wp-mapping/.env
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_SECRET_KEY=your-very-long-secure-random-key

# GitHub OAuth (update URLs to your domain)
GITHUB_CLIENT_ID=your-production-client-id
GITHUB_CLIENT_SECRET=your-production-client-secret

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql://user:password@localhost/ke_wp_mapping
DATABASE_PATH=/var/www/ke-wp-mapping/data/ke_wp_mapping.db

# Admin users
ADMIN_USERS=admin1,admin2,admin3

# Security settings
SESSION_COOKIE_SECURE=true
WTF_CSRF_ENABLED=true

# Performance
RATELIMIT_STORAGE_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/ke-wp-mapping/app.log
```

### 4. Database Setup (PostgreSQL)

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE ke_wp_mapping;
CREATE USER ke_wp_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ke_wp_mapping TO ke_wp_user;
\q
```

### 5. WSGI Configuration

Create `wsgi.py` in project root:
```python
#\!/usr/bin/env python3
"""
WSGI configuration for KE-WP Mapping Application
"""
import os
from app import create_app

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Create application instance
application = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == "__main__":
    application.run()
```

---

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed on your server
- Domain name configured (for production)
- SSL certificate (for HTTPS)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/marvinm2/KE-WP-mapping.git
cd KE-WP-mapping

# Configure environment
cp .env.example .env
# Edit .env with your production values

# Deploy with Docker Compose
docker-compose up -d
```

### Step-by-Step Docker Deployment

#### 1. Server Setup

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose-v2

# Add user to docker group (optional)
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Application Configuration

```bash
# Clone repository
git clone https://github.com/marvinm2/KE-WP-mapping.git
cd KE-WP-mapping

# Create production environment file
cp .env.example .env
```

Edit `.env` with your production values:
```env
# Required OAuth Configuration
GITHUB_CLIENT_ID=your_production_client_id
GITHUB_CLIENT_SECRET=your_production_client_secret
FLASK_SECRET_KEY=your_super_secure_random_key

# Production Settings
FLASK_DEBUG=false
FLASK_ENV=production

# Admin Users (GitHub usernames, comma-separated)
ADMIN_USERS=your_username,other_admin

# Database Configuration
DATABASE_URL=sqlite:///data/ke_wp_mapping.db

# Optional: Redis for caching
RATELIMIT_STORAGE_URL=redis://redis:6379
```

#### 3. GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create new OAuth App:
   - **Name**: "KE-WP Mapping Production"
   - **Homepage URL**: `https://yourdomain.com`
   - **Callback URL**: `https://yourdomain.com/callback`
3. Copy Client ID and Secret to `.env`

#### 4. Database Options

**Option A: Fresh Database (Recommended)**
- Application will create new database automatically
- Users start with empty dataset

**Option B: Deploy with Existing Data**
```bash
# Create data directory and copy existing database
mkdir -p data
cp ke_wp_mapping.db data/
```

#### 5. Deployment Options

**Simple Deployment (Single Container)**
```bash
# Build and run web application only
docker build -t ke-wp-mapping .
docker run -d -p 80:5000 --env-file .env \
  -v $(pwd)/data:/app/data \
  --name ke-wp-app ke-wp-mapping
```

**Production Deployment (Full Stack)**
```bash
# Deploy with nginx, redis, and networking
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs web
```

#### 6. SSL/HTTPS Configuration

For production HTTPS deployment:

```bash
# Install certbot for SSL certificates
sudo apt install certbot

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com

# Create SSL directory and copy certificates
mkdir ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
```

Update `nginx.conf` to enable SSL (example configuration included).

#### 7. DNS Configuration

Point your domain to your server:
```
A Record: yourdomain.com → YOUR_SERVER_IP
```

### Container Architecture

The Docker deployment includes:

- **Web Container**: Flask app with gunicorn (4 workers)
- **Redis Container**: Caching and rate limiting
- **Nginx Container**: Reverse proxy and SSL termination
- **Persistent Volumes**: Database and logs storage

### Management Commands

```bash
# View logs
docker-compose logs -f web
docker-compose logs nginx

# Update application
git pull
docker-compose build web
docker-compose up -d

# Database backup
docker-compose exec web sqlite3 data/ke_wp_mapping.db ".backup backup.db"

# Scale workers
docker-compose up -d --scale web=3

# Stop services
docker-compose down

# Remove all data (careful!)
docker-compose down -v
```

### Monitoring and Health Checks

The application includes built-in health checks:
- Health endpoint: `/health`
- Metrics endpoint: `/metrics`
- Docker health checks every 30 seconds

### Production Features

✅ **Security**: Non-root user, CSRF protection, rate limiting  
✅ **Performance**: Multi-worker gunicorn, Redis caching  
✅ **Reliability**: Health checks, auto-restart, proper logging  
✅ **Scalability**: Horizontal scaling support  
✅ **SSL/HTTPS**: Ready for production TLS termination  

---

**🚀 This deployment guide provides comprehensive production deployment instructions for the KE-WP Mapping Application.**
