# Deployment Guide

## 🚀 Production Deployment

### Prerequisites
- Python 3.8+
- Web server (Apache/Nginx)
- SSL certificate (recommended)
- Domain name

### Backend Deployment

1. **Server Setup:**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd HEALTH_CARE-main/backend
   
   # Create production virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Production Configuration:**
   ```bash
   # Create production .env file
   cp .env.example .env
   
   # Edit .env with production values:
   FLASK_ENV=production
   SECRET_KEY=<strong-random-secret-key>
   DATABASE_URL=<production-database-url>
   OPENAI_API_KEY=<your-openai-key>
   ```

3. **Database Setup:**
   ```bash
   # Initialize production database
   python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

4. **Run with Gunicorn:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 app:app
   ```

### Frontend Deployment

1. **Static File Serving:**
   - Configure web server to serve static files from `frontend/` directory
   - Update API endpoints in JavaScript files if needed

2. **Nginx Configuration Example:**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       # Frontend static files
       location / {
           root /path/to/HEALTH_CARE-main/frontend;
           index index.html;
           try_files $uri $uri/ /index.html;
       }
       
       # Backend API proxy
       location /api/ {
           proxy_pass http://localhost:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       # WebSocket support
       location /socket.io/ {
           proxy_pass http://localhost:5001;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

### SSL Configuration

1. **Let's Encrypt (Recommended):**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

2. **Update Frontend API URLs:**
   - Change `http://localhost:5001` to `https://yourdomain.com` in JavaScript files

### Environment Variables

**Production .env file:**
```env
FLASK_ENV=production
SECRET_KEY=your-super-secret-production-key-here
DATABASE_URL=postgresql://user:password@localhost/healthcare_prod
OPENAI_API_KEY=your-openai-api-key
CORS_ORIGINS=https://yourdomain.com
```

### Security Checklist

- [ ] Use HTTPS in production
- [ ] Set strong SECRET_KEY
- [ ] Configure CORS properly
- [ ] Use production database (PostgreSQL recommended)
- [ ] Set up proper logging
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Backup strategy in place

### Monitoring

1. **Application Monitoring:**
   ```bash
   # Install monitoring tools
   pip install flask-monitoring-dashboard
   ```

2. **Log Management:**
   ```python
   # Add to app.py
   import logging
   from logging.handlers import RotatingFileHandler
   
   if not app.debug:
       file_handler = RotatingFileHandler('logs/healthcare.log', maxBytes=10240, backupCount=10)
       file_handler.setFormatter(logging.Formatter(
           '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
       ))
       file_handler.setLevel(logging.INFO)
       app.logger.addHandler(file_handler)
   ```

### Backup Strategy

1. **Database Backup:**
   ```bash
   # SQLite backup
   cp backend/instance/healthcare.db backup/healthcare_$(date +%Y%m%d).db
   
   # PostgreSQL backup
   pg_dump healthcare_prod > backup/healthcare_$(date +%Y%m%d).sql
   ```

2. **Automated Backups:**
   ```bash
   # Add to crontab
   0 2 * * * /path/to/backup_script.sh
   ```

### Performance Optimization

1. **Frontend:**
   - Minify CSS and JavaScript
   - Optimize images
   - Enable gzip compression
   - Use CDN for static assets

2. **Backend:**
   - Use connection pooling
   - Implement caching (Redis)
   - Optimize database queries
   - Use async operations where possible

### Health Checks

Create health check endpoints:
```python
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
```

### Troubleshooting

**Common Production Issues:**

1. **CORS Errors:**
   - Check CORS_ORIGINS in .env
   - Verify frontend domain matches

2. **Database Connection:**
   - Check DATABASE_URL format
   - Verify database server is running

3. **WebSocket Issues:**
   - Ensure proxy configuration supports WebSockets
   - Check firewall rules

4. **SSL Certificate:**
   - Verify certificate is valid
   - Check certificate renewal

### Scaling Considerations

1. **Horizontal Scaling:**
   - Use load balancer
   - Implement session storage (Redis)
   - Database clustering

2. **Vertical Scaling:**
   - Increase server resources
   - Optimize application performance
   - Database tuning