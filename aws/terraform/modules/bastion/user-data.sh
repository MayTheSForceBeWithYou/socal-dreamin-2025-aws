#!/bin/bash

# Bastion Host User Data Script
# This script sets up an nginx reverse proxy to OpenSearch

set -e

# Update system
yum update -y

# Install nginx
yum install -y nginx

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install jq for JSON processing
yum install -y jq

# Create nginx configuration for OpenSearch proxy
cat > /etc/nginx/conf.d/opensearch.conf << 'EOF'
upstream opensearch {
    server ${opensearch_endpoint}:443;
}

server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # Self-signed SSL certificate for local proxy
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Proxy settings
    proxy_ssl_verify off;
    proxy_ssl_server_name on;
    proxy_ssl_name ${opensearch_endpoint};
    
    # Headers for OpenSearch
    proxy_set_header Host ${opensearch_endpoint};
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Port $server_port;
    
    # Disable buffering for real-time streaming
    proxy_buffering off;
    proxy_request_buffering off;
    
    # Timeout settings
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # Handle CORS
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range' always;
    
    # Handle preflight requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS';
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization';
        add_header 'Access-Control-Max-Age' 1728000;
        add_header 'Content-Type' 'text/plain; charset=utf-8';
        add_header 'Content-Length' 0;
        return 204;
    }
    
    # Proxy all requests to OpenSearch
    location / {
        proxy_pass https://opensearch;
        
        # Handle WebSocket connections for Dashboards
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Create SSL certificate directory
mkdir -p /etc/nginx/ssl

# Generate self-signed SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt \
    -subj "/C=US/ST=CA/L=San Francisco/O=OpenSearch Proxy/CN=bastion"

# Set proper permissions
chmod 600 /etc/nginx/ssl/nginx.key
chmod 644 /etc/nginx/ssl/nginx.crt

# Start and enable nginx
systemctl start nginx
systemctl enable nginx

# Create a simple health check script
cat > /usr/local/bin/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for the bastion host

# Check if nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "ERROR: nginx is not running"
    exit 1
fi

# Check if we can reach OpenSearch
OPENSEARCH_ENDPOINT="${opensearch_endpoint}"
if ! curl -s --connect-timeout 10 "https://$OPENSEARCH_ENDPOINT" > /dev/null; then
    echo "ERROR: Cannot reach OpenSearch endpoint"
    exit 1
fi

echo "OK: Bastion host is healthy"
exit 0
EOF

chmod +x /usr/local/bin/health-check.sh

# Create a systemd service for health checks
cat > /etc/systemd/system/bastion-health-check.service << 'EOF'
[Unit]
Description=Bastion Host Health Check
After=nginx.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/health-check.sh
User=root
EOF

# Create a systemd timer for periodic health checks
cat > /etc/systemd/system/bastion-health-check.timer << 'EOF'
[Unit]
Description=Run Bastion Health Check every 5 minutes
Requires=bastion-health-check.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# Enable and start the health check timer
systemctl daemon-reload
systemctl enable bastion-health-check.timer
systemctl start bastion-health-check.timer

# Log completion
echo "Bastion host setup completed at $(date)" >> /var/log/bastion-setup.log
echo "OpenSearch endpoint: ${opensearch_endpoint}" >> /var/log/bastion-setup.log
echo "Nginx status: $(systemctl is-active nginx)" >> /var/log/bastion-setup.log
