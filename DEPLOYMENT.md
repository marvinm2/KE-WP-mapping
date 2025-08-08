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

**🚀 This deployment guide provides comprehensive production deployment instructions for the KE-WP Mapping Application.**
EOF < /dev/null
