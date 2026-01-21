#!/bin/bash

# ClarityGR MongoDB Service Diagnostic Script
# Diagnoses and fixes MongoDB service startup issues

# Set up logging
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

log "INFO" "🔧 MongoDB Service Diagnostic and Repair"
log "INFO" "========================================"

# Check MongoDB service status
check_service_status() {
    log "STEP" "🔍 Checking MongoDB service status..."
    
    # Check if service is active
    if systemctl is-active --quiet mongod; then
        log "SUCCESS" "✅ MongoDB service is running"
        return 0
    else
        log "ERROR" "❌ MongoDB service is NOT running"
        
        # Check if service is enabled
        if systemctl is-enabled --quiet mongod; then
            log "INFO" "✅ MongoDB service is enabled for boot"
        else
            log "WARN" "⚠️ MongoDB service is NOT enabled for boot"
        fi
        
        return 1
    fi
}

# Check MongoDB logs for errors
check_mongodb_logs() {
    log "STEP" "📋 Checking MongoDB logs for errors..."
    
    # Check systemd journal logs
    log "INFO" "🔍 Recent MongoDB service logs:"
    local recent_logs=$(sudo journalctl -u mongod --since "10 minutes ago" --no-pager -n 20 2>/dev/null)
    if [ -n "$recent_logs" ]; then
        echo "$recent_logs" | while IFS= read -r line; do
            if echo "$line" | grep -qi "error\|fail\|fatal"; then
                log "ERROR" "   🚨 $line"
            elif echo "$line" | grep -qi "warn"; then
                log "WARN" "   ⚠️ $line"
            else
                log "INFO" "   📋 $line"
            fi
        done
    else
        log "INFO" "   No recent systemd logs found"
    fi
    
    # Check MongoDB log file
    local log_file="/var/log/mongodb/mongod.log"
    if [ -f "$log_file" ]; then
        log "INFO" "🔍 Recent MongoDB log file entries:"
        local recent_file_logs=$(tail -20 "$log_file" 2>/dev/null)
        if [ -n "$recent_file_logs" ]; then
            echo "$recent_file_logs" | while IFS= read -r line; do
                if echo "$line" | grep -qi "error\|fail\|fatal"; then
                    log "ERROR" "   🚨 $line"
                elif echo "$line" | grep -qi "warn"; then
                    log "WARN" "   ⚠️ $line"
                else
                    log "INFO" "   📋 $line"
                fi
            done
        else
            log "WARN" "   MongoDB log file is empty or unreadable"
        fi
    else
        log "WARN" "   MongoDB log file not found: $log_file"
    fi
}

# Check MongoDB configuration
check_configuration() {
    log "STEP" "⚙️ Checking MongoDB configuration..."
    
    local config_file="/etc/mongod.conf"
    if [ ! -f "$config_file" ]; then
        log "ERROR" "❌ MongoDB configuration file not found: $config_file"
        return 1
    fi
    
    log "INFO" "✅ Configuration file exists: $config_file"
    
    # Check for syntax issues
    if command -v mongod >/dev/null 2>&1; then
        log "INFO" "🔍 Testing configuration syntax..."
        local config_test=$(mongod --config "$config_file" --test 2>&1)
        local config_exit_code=$?
        
        if [ $config_exit_code -eq 0 ]; then
            log "SUCCESS" "✅ Configuration syntax is valid"
        else
            log "ERROR" "❌ Configuration syntax error:"
            echo "$config_test" | while IFS= read -r line; do
                log "ERROR" "   $line"
            done
            return 1
        fi
    else
        log "WARN" "⚠️ mongod binary not found, cannot test configuration"
    fi
    
    # Check critical configuration settings
    log "INFO" "🔍 Configuration analysis:"
    
    local port=$(grep -E "^\s*port:" "$config_file" | awk '{print $2}' 2>/dev/null || echo "27017")
    log "INFO" "   Port: $port"
    
    local bind_ip=$(grep -E "^\s*bindIp:" "$config_file" | awk '{print $2}' | tr -d '"' 2>/dev/null || echo "127.0.0.1")
    log "INFO" "   Bind IP: $bind_ip"
    
    local db_path=$(grep -E "^\s*dbPath:" "$config_file" | awk '{print $2}' 2>/dev/null || echo "/var/lib/mongodb")
    log "INFO" "   Database Path: $db_path"
    
    # Check if database directory exists and has correct permissions
    if [ -d "$db_path" ]; then
        local db_owner=$(stat -c '%U' "$db_path" 2>/dev/null || echo "unknown")
        log "INFO" "   Database directory owner: $db_owner"
        
        if [ "$db_owner" != "mongodb" ]; then
            log "WARN" "⚠️ Database directory not owned by mongodb user"
            log "INFO" "🔧 Fixing database directory ownership..."
            if sudo chown -R mongodb:mongodb "$db_path"; then
                log "SUCCESS" "✅ Fixed database directory ownership"
            else
                log "ERROR" "❌ Failed to fix database directory ownership"
            fi
        fi
    else
        log "ERROR" "❌ Database directory does not exist: $db_path"
        log "INFO" "🔧 Creating database directory..."
        if sudo mkdir -p "$db_path" && sudo chown mongodb:mongodb "$db_path"; then
            log "SUCCESS" "✅ Created database directory"
        else
            log "ERROR" "❌ Failed to create database directory"
        fi
    fi
    
    return 0
}

# Check port conflicts
check_port_conflicts() {
    log "STEP" "🔍 Checking for port conflicts..."
    
    local mongodb_port="27017"
    local port_usage=$(netstat -tlnp 2>/dev/null | grep ":$mongodb_port " || echo "")
    
    if [ -n "$port_usage" ]; then
        log "WARN" "⚠️ Port $mongodb_port is in use:"
        echo "$port_usage" | while IFS= read -r line; do
            log "WARN" "   📋 $line"
        done
        
        if echo "$port_usage" | grep -q mongod; then
            log "INFO" "✅ Port used by MongoDB (expected)"
        else
            log "ERROR" "❌ Port used by another service - this could prevent MongoDB from starting"
            return 1
        fi
    else
        log "SUCCESS" "✅ Port $mongodb_port is available"
    fi
    
    return 0
}

# Fix MongoDB service
fix_mongodb_service() {
    log "STEP" "🔧 Attempting to fix MongoDB service..."
    
    # Reload systemd daemon
    log "INFO" "🔄 Reloading systemd daemon..."
    sudo systemctl daemon-reload
    
    # Stop any existing MongoDB processes
    log "INFO" "🛑 Stopping any existing MongoDB processes..."
    sudo systemctl stop mongod 2>/dev/null || true
    sleep 2
    
    # Kill any remaining MongoDB processes
    local mongo_pids=$(pgrep mongod || echo "")
    if [ -n "$mongo_pids" ]; then
        log "INFO" "🔧 Killing remaining MongoDB processes..."
        sudo pkill mongod 2>/dev/null || true
        sleep 2
    fi
    
    # Enable the service
    log "INFO" "🔧 Enabling MongoDB service..."
    if sudo systemctl enable mongod; then
        log "SUCCESS" "✅ MongoDB service enabled"
    else
        log "WARN" "⚠️ Could not enable MongoDB service"
    fi
    
    # Start the service
    log "INFO" "🚀 Starting MongoDB service..."
    if sudo systemctl start mongod; then
        log "SUCCESS" "✅ MongoDB service start command executed"
    else
        log "ERROR" "❌ Failed to start MongoDB service"
        return 1
    fi
    
    # Wait for service to stabilize
    log "INFO" "⏳ Waiting for MongoDB service to stabilize..."
    sleep 5
    
    # Check if service is now active
    if systemctl is-active --quiet mongod; then
        log "SUCCESS" "✅ MongoDB service is now running"
    else
        log "ERROR" "❌ MongoDB service failed to start"
        log "INFO" "🔍 Checking service status for more details..."
        sudo systemctl status mongod --no-pager || true
        return 1
    fi
    
    return 0
}

# Verify MongoDB is listening
verify_listening() {
    log "STEP" "🔍 Verifying MongoDB is listening on ports..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local listening_ports=$(netstat -tlnp 2>/dev/null | grep mongod | awk '{print $4}' || echo "")
        
        if [ -n "$listening_ports" ]; then
            log "SUCCESS" "🎉 MongoDB is now listening on ports:"
            echo "$listening_ports" | while IFS= read -r port_info; do
                log "SUCCESS" "   ✅ $port_info"
            done
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log "ERROR" "❌ MongoDB not listening after $max_attempts attempts"
            return 1
        fi
        
        log "INFO" "⏳ Attempt $attempt/$max_attempts - waiting for MongoDB to start listening..."
        sleep 2
        ((attempt++))
    done
}

# Test MongoDB connection
test_connection() {
    log "STEP" "🧪 Testing MongoDB connection..."
    
    if command -v mongosh >/dev/null 2>&1; then
        if mongosh --eval "db.runCommand({ping: 1})" >/dev/null 2>&1; then
            log "SUCCESS" "🎉 MongoDB connection test successful!"
            return 0
        else
            log "ERROR" "❌ MongoDB connection test failed"
            return 1
        fi
    else
        log "WARN" "⚠️ mongosh not available for connection testing"
        return 0
    fi
}

# Main diagnostic function
main() {
    log "INFO" "🚀 Starting MongoDB service diagnosis..."
    
    # Step 1: Check service status
    local service_running=false
    if check_service_status; then
        service_running=true
    fi
    
    # Step 2: Check logs regardless of service status
    check_mongodb_logs
    
    # Step 3: Check configuration
    if ! check_configuration; then
        log "ERROR" "❌ Configuration issues found"
        return 1
    fi
    
    # Step 4: Check port conflicts
    check_port_conflicts
    
    # Step 5: If service is not running, try to fix it
    if [ "$service_running" = false ]; then
        log "INFO" "🔧 Service not running - attempting to fix..."
        if fix_mongodb_service; then
            log "SUCCESS" "✅ Service fix completed"
        else
            log "ERROR" "❌ Service fix failed"
            return 1
        fi
    fi
    
    # Step 6: Verify MongoDB is listening
    if verify_listening; then
        log "SUCCESS" "✅ MongoDB is listening correctly"
    else
        log "ERROR" "❌ MongoDB is not listening on ports"
        return 1
    fi
    
    # Step 7: Test connection
    if test_connection; then
        log "SUCCESS" "✅ MongoDB connection verified"
    else
        log "WARN" "⚠️ MongoDB connection test had issues"
    fi
    
    # Final status
    log "SUCCESS" "🎉 MongoDB service diagnosis and repair completed!"
    log "INFO" "✅ MongoDB should now be running and accessible"
    
    return 0
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 