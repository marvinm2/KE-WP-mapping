# KE-WP Mapping - Deployment Guide

## Production Deployment with Docker

### 1. Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB RAM and 10GB disk space

### 2. Environment Setup

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd KE-WP-mapping
   cp .env.example .env
   ```

2. **Configure environment variables in `.env`:**
   ```bash
   # GitHub OAuth (required)
   GITHUB_CLIENT_ID=your_real_github_client_id
   GITHUB_CLIENT_SECRET=your_real_github_client_secret
   
   # Security (required)
   FLASK_SECRET_KEY=your_super_secure_random_secret_key_here
   
   # Optional
   FLASK_DEBUG=false
   ```

### 3. Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f web
```

### 4. Services

- **Web Application**: http://localhost (nginx reverse proxy)
- **Direct App Access**: http://localhost:5000 (development only)
- **Redis Cache**: localhost:6379
- **Health Check**: http://localhost/health

### 5. SSL/HTTPS Setup (Optional)

1. **Obtain SSL certificates** (Let's Encrypt recommended):
   ```bash
   # Example with certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Update nginx configuration** in `nginx.conf`:
   - Uncomment HTTPS server block
   - Update paths to your certificates
   - Update server_name to your domain

3. **Restart nginx**:
   ```bash
   docker-compose restart nginx
   ```

## Manual Deployment (Without Docker)

### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv sqlite3 nginx redis-server
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip sqlite nginx redis
sudo systemctl enable redis
sudo systemctl start redis
```

### 2. Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/ke-wp-mapping
cd /var/www/ke-wp-mapping

# Clone repository
git clone <repository-url> .

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your values

# Initialize database
python migrate_csv_to_db.py
```

### 3. Systemd Service

Create `/etc/systemd/system/ke-wp-mapping.service`:

```ini
[Unit]
Description=KE-WP Mapping Flask Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/ke-wp-mapping
Environment=PATH=/var/www/ke-wp-mapping/venv/bin
EnvironmentFile=/var/www/ke-wp-mapping/.env
ExecStart=/var/www/ke-wp-mapping/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ke-wp-mapping
sudo systemctl start ke-wp-mapping
```

### 4. Nginx Configuration

Create `/etc/nginx/sites-available/ke-wp-mapping`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Static files
    location /static/ {
        alias /var/www/ke-wp-mapping/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/ke-wp-mapping /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Monitoring and Maintenance

### 1. Application Metrics

- **Health Check**: `curl http://localhost/health`
- **System Metrics**: `curl http://localhost/metrics`
- **Endpoint Metrics**: `curl http://localhost/metrics/submit`

### 2. Database Maintenance

```bash
# Backup database
make backup-db

# Restore from backup
make restore-db BACKUP_FILE=backup_file.db

# Clean old cache entries (automatic, but can be triggered)
sqlite3 ke_wp_mapping.db "DELETE FROM sparql_cache WHERE expires_at <= datetime('now')"
```

### 3. Log Management

```bash
# Docker logs
docker-compose logs -f web
docker-compose logs --tail=100 nginx

# System logs (manual deployment)
sudo journalctl -u ke-wp-mapping -f
sudo tail -f /var/log/nginx/access.log
```

### 4. Performance Tuning

**For high traffic:**

1. **Increase gunicorn workers**:
   ```bash
   # In docker-compose.yml or systemd service
   --workers 8  # 2 × CPU cores
   ```

2. **Redis configuration**:
   ```bash
   # In docker-compose.yml, add Redis config
   command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

3. **Database optimization**:
   ```sql
   -- Run periodically to maintain performance
   VACUUM;
   ANALYZE;
   ```

## Security Considerations

### 1. Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22     # SSH
sudo ufw allow 80     # HTTP
sudo ufw allow 443    # HTTPS
sudo ufw enable
```

### 2. Regular Updates

```bash
# Update application
git pull origin main
docker-compose build --no-cache web
docker-compose up -d

# Update system packages
sudo apt update && sudo apt upgrade
```

### 3. Backup Strategy

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp /var/www/ke-wp-mapping/ke_wp_mapping.db /backups/ke_wp_mapping_$DATE.db
find /backups -name "ke_wp_mapping_*.db" -mtime +30 -delete
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change ports in docker-compose.yml
2. **Permission errors**: Check file ownership and permissions
3. **Database lock**: Restart application, check for zombie processes
4. **Memory issues**: Increase container limits or server resources
5. **SSL certificate issues**: Verify certificate paths and permissions

### Debug Mode

```bash
# Enable debug logging (development only)
export FLASK_DEBUG=true
docker-compose restart web
```

### Performance Issues

1. **Check metrics**: Visit `/metrics` endpoint
2. **Monitor resource usage**: `docker stats`
3. **Check slow queries**: Review application logs
4. **Verify cache hits**: Check SPARQL cache table

## Scaling for Production

### Load Balancing

For high availability, use multiple app instances behind a load balancer:

```yaml
# docker-compose.yml
services:
  web1:
    build: .
    # ... config
  web2:
    build: .
    # ... config
  
  nginx:
    # Update nginx.conf to include both web1 and web2
```

### Database Scaling

For large datasets, consider:
1. **PostgreSQL**: Replace SQLite with PostgreSQL
2. **Read replicas**: For read-heavy workloads
3. **Connection pooling**: Use pgbouncer or similar
4. **Database partitioning**: For time-series data