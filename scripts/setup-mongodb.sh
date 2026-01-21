#!/bin/bash

echo "Setting up MongoDB Search Community Docker image..."

# Download the MongoDB Search Community Docker image
echo "Downloading MongoDB Search Community 1.47.0..."
wget -O mongodb-search-community-1.47.0-amd64.tar.gz \
    https://downloads.mongodb.org/mongodb-search-community/1.47.0/docker/mongodb-search-community-1.47.0-amd64.tar.gz

# Load the Docker image
echo "Loading MongoDB Search Community image into Docker..."
docker load -i mongodb-search-community-1.47.0-amd64.tar.gz

# Clean up the tar.gz file
echo "Cleaning up downloaded file..."
rm mongodb-search-community-1.47.0-amd64.tar.gz

echo "MongoDB Search Community image setup complete!"
echo "You can now run 'docker-compose up' to start the services." 