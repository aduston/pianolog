#!/bin/bash
# Setup script for nginx to serve pianolog

set -e

echo "Installing nginx..."
sudo apt-get update
sudo apt-get install -y nginx

echo "Creating nginx configuration..."
sudo tee /etc/nginx/sites-available/pianolog > /dev/null <<'EOF'
server {
    listen 80;
    server_name raspberrypi.local;

    location /pianolog {
        return 301 /pianolog/;
    }

    location /pianolog/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_read_timeout 86400;
        proxy_buffering off;
    }

    location / {
        root /var/www/html;
        index index.html index.htm;
    }
}
EOF

echo "Enabling pianolog site..."
sudo ln -sf /etc/nginx/sites-available/pianolog /etc/nginx/sites-enabled/pianolog

echo "Removing default site if it exists..."
sudo rm -f /etc/nginx/sites-enabled/default

echo "Testing nginx configuration..."
sudo nginx -t

echo "Restarting nginx..."
sudo systemctl restart nginx

echo "Enabling nginx to start on boot..."
sudo systemctl enable nginx

echo ""
echo "✓ Nginx setup complete!"
echo "✓ The web interface will be available at: http://raspberrypi.local/pianolog"
echo ""
echo "Make sure pianolog is running with the web server enabled."
