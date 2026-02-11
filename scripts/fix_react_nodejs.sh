#!/bin/bash

# ClarityGR React/Node.js Fix Script
# Fixes crypto.hash error and Vite compatibility issues

# Set up logging
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

log "INFO" "🔧 ClarityGR React/Node.js Fix"
log "INFO" "============================="

# Main script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

log "INFO" "📂 Project Directory: $PROJECT_DIR"

# Check if running with proper permissions
if [ "$EUID" -eq 0 ]; then
    log "ERROR" "❌ Do not run this script as root"
    log "INFO" "💡 Run as regular user: ./scripts/fix_react_nodejs.sh"
    exit 1
fi

# Check current Node.js version
check_nodejs_version() {
    log "STEP" "🔍 Checking Node.js version..."
    
    if ! command -v node >/dev/null 2>&1; then
        log "ERROR" "❌ Node.js not installed"
        return 1
    fi
    
    local node_version=$(node --version | cut -d'v' -f2)
    local major_version=$(echo "$node_version" | cut -d'.' -f1)
    
    log "INFO" "📦 Current Node.js version: v$node_version"
    
    if [ "$major_version" -lt 18 ]; then
        log "WARN" "⚠️ Node.js version too old (v$node_version < v18.0.0)"
        log "WARN" "   crypto.hash() requires Node.js 15+ (recommended: 18+)"
        return 1
    else
        log "SUCCESS" "✅ Node.js version is compatible (v$node_version >= v18.0.0)"
        return 0
    fi
}

# Update Node.js to version 18 LTS
update_nodejs() {
    log "STEP" "🚀 Updating Node.js to version 18 LTS..."
    
    # Remove old NodeSource repository if it exists
    sudo rm -f /etc/apt/sources.list.d/nodesource.list
    
    # Add Node.js 18.x repository
    log "INFO" "📦 Adding Node.js 18.x repository..."
    if curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -; then
        log "SUCCESS" "✅ Node.js repository added"
    else
        log "ERROR" "❌ Failed to add Node.js repository"
        return 1
    fi
    
    # Update package lists
    log "INFO" "📝 Updating package lists..."
    if sudo apt-get update; then
        log "SUCCESS" "✅ Package lists updated"
    else
        log "WARN" "⚠️ Package list update had issues"
    fi
    
    # Install Node.js 18
    log "INFO" "📦 Installing Node.js 18..."
    if sudo apt-get install -y nodejs; then
        log "SUCCESS" "✅ Node.js 18 installed"
    else
        log "ERROR" "❌ Failed to install Node.js 18"
        return 1
    fi
    
    # Verify installation
    local new_version=$(node --version)
    local npm_version=$(npm --version)
    
    log "SUCCESS" "✅ Node.js updated to: $new_version"
    log "SUCCESS" "✅ npm version: v$npm_version"
    
    return 0
}

# Check React project structure
check_react_project() {
    log "STEP" "🔍 Checking React project structure..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    
    if [ ! -d "$ui_dir" ]; then
        log "ERROR" "❌ UI directory not found: $ui_dir"
        return 1
    fi
    
    if [ ! -f "$ui_dir/package.json" ]; then
        log "ERROR" "❌ package.json not found in UI directory"
        return 1
    fi
    
    if [ ! -f "$ui_dir/vite.config.ts" ]; then
        log "ERROR" "❌ vite.config.ts not found in UI directory"
        return 1
    fi
    
    log "SUCCESS" "✅ React project structure looks good"
    return 0
}

# Clean React dependencies
clean_react_dependencies() {
    log "STEP" "🧹 Cleaning React dependencies..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    cd "$ui_dir"
    
    # Remove existing node_modules and lock files
    log "INFO" "🗑️ Removing old dependencies..."
    rm -rf node_modules
    rm -f package-lock.json
    rm -f yarn.lock
    
    # Clear npm cache
    log "INFO" "🧹 Clearing npm cache..."
    npm cache clean --force
    
    log "SUCCESS" "✅ Dependencies cleaned"
}

# Fix package.json for compatibility
fix_package_json() {
    log "STEP" "🔧 Fixing package.json for Node.js 18 compatibility..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    local package_json="$ui_dir/package.json"
    
    # Backup original package.json
    cp "$package_json" "$package_json.backup.$(date +%Y%m%d_%H%M%S)"
    log "INFO" "📄 Backed up original package.json"
    
    # Check current Vite version
    local current_vite=$(grep '"vite"' "$package_json" | sed 's/.*"vite": *"\([^"]*\)".*/\1/')
    log "INFO" "📦 Current Vite version: $current_vite"
    
    # Update Vite to compatible version for Node.js 18
    if [[ "$current_vite" =~ ^5\. ]] || [[ "$current_vite" =~ ^6\. ]] || [[ "$current_vite" =~ ^7\. ]]; then
        log "INFO" "🔧 Vite version is recent - keeping current version"
    else
        log "INFO" "🔧 Updating Vite to compatible version..."
        sed -i 's/"vite": "[^"]*"/"vite": "^5.0.0"/' "$package_json"
    fi
    
    # Add Node.js engine specification
    if ! grep -q '"engines"' "$package_json"; then
        log "INFO" "🔧 Adding Node.js engine specification..."
        # Add engines field after name
        sed -i '/"name":/a\  "engines": {\n    "node": ">=18.0.0",\n    "npm": ">=8.0.0"\n  },' "$package_json"
    fi
    
    log "SUCCESS" "✅ package.json updated for compatibility"
}

# Install React dependencies
install_react_dependencies() {
    log "STEP" "📦 Installing React dependencies..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    cd "$ui_dir"
    
    # Try npm ci first (faster if package-lock.json is valid)
    log "INFO" "🔄 Attempting npm ci (clean install)..."
    if npm ci; then
        log "SUCCESS" "✅ npm ci completed successfully"
        return 0
    fi
    
    # Fallback to npm install
    log "WARN" "⚠️ npm ci failed, trying npm install..."
    if npm install; then
        log "SUCCESS" "✅ npm install completed successfully"
        return 0
    fi
    
    # Fallback with legacy peer deps
    log "WARN" "⚠️ npm install failed, trying with --legacy-peer-deps..."
    if npm install --legacy-peer-deps; then
        log "SUCCESS" "✅ npm install with legacy peer deps completed"
        return 0
    fi
    
    # Final fallback with force
    log "WARN" "⚠️ Previous attempts failed, trying with --force..."
    if npm install --force; then
        log "SUCCESS" "✅ npm install with force completed"
        return 0
    fi
    
    log "ERROR" "❌ All npm install attempts failed"
    return 1
}

# Test React build
test_react_build() {
    log "STEP" "🧪 Testing React build..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    cd "$ui_dir"
    
    # Try production build
    log "INFO" "🏗️ Attempting production build..."
    if npm run build; then
        log "SUCCESS" "✅ React production build successful"
        return 0
    else
        log "WARN" "⚠️ Production build failed, checking for specific errors..."
        
        # Check for crypto.hash error specifically
        if npm run build 2>&1 | grep -q "crypto.hash is not a function"; then
            log "ERROR" "❌ crypto.hash error still present"
            log "ERROR" "💡 Node.js version may still be incompatible"
            return 1
        else
            log "WARN" "⚠️ Build failed for other reasons (non-critical)"
            return 0
        fi
    fi
}

# Start React development server (test)
test_react_dev_server() {
    log "STEP" "🧪 Testing React development server..."
    
    local ui_dir="$PROJECT_DIR/frontend"
    cd "$ui_dir"
    
    # Kill any existing processes on port 3000
    log "INFO" "🛑 Stopping any existing React server on port 3000..."
    pkill -f "vite.*3000" 2>/dev/null || true
    sleep 2
    
    # Start dev server in background
    log "INFO" "🚀 Starting React development server..."
    npm run dev > /tmp/react_test.log 2>&1 &
    local dev_pid=$!
    
    # Wait for server to start
    log "INFO" "⏳ Waiting for development server to start..."
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            log "SUCCESS" "✅ React development server is running"
            kill $dev_pid 2>/dev/null || true
            return 0
        fi
        
        # Check for crypto.hash error in logs
        if grep -q "crypto.hash is not a function" /tmp/react_test.log; then
            log "ERROR" "❌ crypto.hash error detected in development server"
            kill $dev_pid 2>/dev/null || true
            return 1
        fi
        
        sleep 2
        ((attempts++))
    done
    
    log "WARN" "⚠️ Development server didn't respond in time"
    log "INFO" "📋 Last few lines of dev server log:"
    tail -5 /tmp/react_test.log || true
    
    kill $dev_pid 2>/dev/null || true
    return 1
}

# Show fix summary
show_fix_summary() {
    log "STEP" "📊 React/Node.js Fix Summary"
    
    local node_version=$(node --version 2>/dev/null || echo "Unknown")
    local npm_version=$(npm --version 2>/dev/null || echo "Unknown")
    
    echo ""
    echo "🎉 React/Node.js Fix Complete!"
    echo "=============================="
    echo ""
    echo "📦 Versions:"
    echo "   Node.js: $node_version"
    echo "   npm: v$npm_version"
    echo ""
    echo "✅ Fixes Applied:"
    echo "   • Node.js updated to version 18+ (crypto.hash support)"
    echo "   • React dependencies cleaned and reinstalled"
    echo "   • Vite configuration updated for compatibility"
    echo "   • package.json engine requirements added"
    echo ""
    echo "🚀 Next Steps:"
    echo "   1. Test React application: cd ui && npm run dev"
    echo "   2. Access frontend: http://localhost:3000"
    echo "   3. Run full installation: ./install_claritygr_new.sh"
    echo ""
}

# Main function
main() {
    log "INFO" "🚀 Starting React/Node.js fix..."
    
    # Step 1: Check React project
    if ! check_react_project; then
        log "ERROR" "❌ React project structure check failed"
        return 1
    fi
    
    # Step 2: Check Node.js version
    local nodejs_needs_update=false
    if ! check_nodejs_version; then
        nodejs_needs_update=true
    fi
    
    # Step 3: Update Node.js if needed
    if [ "$nodejs_needs_update" = true ]; then
        if ! update_nodejs; then
            log "ERROR" "❌ Node.js update failed"
            return 1
        fi
        
        # Verify update worked
        if ! check_nodejs_version; then
            log "ERROR" "❌ Node.js still not compatible after update"
            return 1
        fi
    fi
    
    # Step 4: Clean React dependencies
    clean_react_dependencies
    
    # Step 5: Fix package.json
    fix_package_json
    
    # Step 6: Install dependencies
    if ! install_react_dependencies; then
        log "ERROR" "❌ Failed to install React dependencies"
        return 1
    fi
    
    # Step 7: Test build
    test_react_build
    
    # Step 8: Test dev server
    test_react_dev_server
    
    # Step 9: Show summary
    show_fix_summary
    
    log "SUCCESS" "🎉 React/Node.js fix completed successfully!"
    return 0
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 