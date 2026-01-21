#!/bin/bash

# ClarityGR Master Fix Script
# Fixes all major issues: MongoDB corruption, Mistral quantization, React/Node.js

# Set up logging
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log "INFO" "🔧 ClarityGR Master Fix Script"
log "INFO" "============================="

# Main script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

log "INFO" "📂 Project Directory: $PROJECT_DIR"

# Check if running with proper permissions
if [ "$EUID" -eq 0 ]; then
    log "ERROR" "❌ Do not run this script as root"
    log "INFO" "💡 Run as regular user: ./scripts/fix_all_issues.sh"
    exit 1
fi

# Track fix results
declare -A FIX_RESULTS
TOTAL_FIXES=0
SUCCESSFUL_FIXES=0
FAILED_FIXES=0

# Record fix result
record_fix_result() {
    local fix_name="$1"
    local result="$2"
    
    FIX_RESULTS["$fix_name"]="$result"
    TOTAL_FIXES=$((TOTAL_FIXES + 1))
    
    if [ "$result" = "SUCCESS" ]; then
        SUCCESSFUL_FIXES=$((SUCCESSFUL_FIXES + 1))
        log "SUCCESS" "✅ $fix_name: SUCCESS"
    else
        FAILED_FIXES=$((FAILED_FIXES + 1))
        log "ERROR" "❌ $fix_name: FAILED"
    fi
}

# Show banner
show_banner() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                    ClarityGR Fix Suite                       ║${NC}"
    echo -e "${BLUE}║              Comprehensive System Repair                    ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}🎯 This script will fix the following issues:${NC}"
    echo "   1. 🗄️  MongoDB dependency corruption"
    echo "   2. 🤖 Mistral AI quantization errors"
    echo "   3. ⚛️  React/Node.js crypto.hash errors"
    echo "   4. 🧪 System validation and testing"
    echo ""
}

# Ask for confirmation
ask_confirmation() {
    echo -e "${YELLOW}⚠️  WARNING: This will make system-wide changes${NC}"
    echo "   • MongoDB will be completely removed and reinstalled"
    echo "   • Node.js will be updated to version 18+"
    echo "   • React dependencies will be cleaned and reinstalled"
    echo "   • Mistral AI client code will be modified"
    echo ""
    echo -e "${RED}💾 Backups will be created automatically${NC}"
    echo ""
    
    read -p "Continue with comprehensive system fix? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "🚫 Fix cancelled by user"
        exit 0
    fi
    
    echo ""
    log "INFO" "✅ User confirmed - proceeding with fixes"
}

# Check system prerequisites
check_prerequisites() {
    log "STEP" "🔍 Checking system prerequisites..."
    
    local issues_found=false
    
    # Check if we're on Ubuntu/Debian
    if ! command -v apt-get >/dev/null 2>&1; then
        log "ERROR" "❌ This script requires Ubuntu/Debian (apt-get not found)"
        issues_found=true
    fi
    
    # Check internet connectivity
    if ! curl -s --connect-timeout 5 https://google.com >/dev/null; then
        log "ERROR" "❌ No internet connectivity - required for Node.js updates"
        issues_found=true
    fi
    
    # Check disk space (need at least 2GB free)
    local free_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$free_space" -lt 2097152 ]; then  # 2GB in KB
        log "WARN" "⚠️ Low disk space - may cause issues during fixes"
    fi
    
    if [ "$issues_found" = true ]; then
        log "ERROR" "❌ Prerequisites check failed"
        return 1
    fi
    
    log "SUCCESS" "✅ Prerequisites check passed"
    return 0
}

# Fix 1: MongoDB Corruption
fix_mongodb_corruption() {
    log "STEP" "🗄️ Fix 1/3: MongoDB Corruption Recovery"
    echo ""
    
    local mongodb_fix_script="$SCRIPT_DIR/fix_mongodb_corruption.sh"
    
    if [ ! -f "$mongodb_fix_script" ]; then
        log "ERROR" "❌ MongoDB fix script not found: $mongodb_fix_script"
        record_fix_result "MongoDB Corruption" "FAILED"
        return 1
    fi
    
    log "INFO" "🚀 Running MongoDB corruption recovery..."
    if bash "$mongodb_fix_script"; then
        record_fix_result "MongoDB Corruption" "SUCCESS"
        return 0
    else
        record_fix_result "MongoDB Corruption" "FAILED"
        return 1
    fi
}

# Fix 2: Mistral AI Quantization
fix_mistral_quantization() {
    log "STEP" "🤖 Fix 2/3: Mistral AI Quantization"
    echo ""
    
    local mistral_fix_script="$SCRIPT_DIR/fix_mistral_quantization.sh"
    
    if [ ! -f "$mistral_fix_script" ]; then
        log "ERROR" "❌ Mistral fix script not found: $mistral_fix_script"
        record_fix_result "Mistral Quantization" "FAILED"
        return 1
    fi
    
    log "INFO" "🚀 Running Mistral quantization fix..."
    if bash "$mistral_fix_script"; then
        record_fix_result "Mistral Quantization" "SUCCESS"
        return 0
    else
        record_fix_result "Mistral Quantization" "FAILED"
        return 1
    fi
}

# Fix 3: React/Node.js
fix_react_nodejs() {
    log "STEP" "⚛️ Fix 3/3: React/Node.js Compatibility"
    echo ""
    
    local react_fix_script="$SCRIPT_DIR/fix_react_nodejs.sh"
    
    if [ ! -f "$react_fix_script" ]; then
        log "ERROR" "❌ React fix script not found: $react_fix_script"
        record_fix_result "React/Node.js" "FAILED"
        return 1
    fi
    
    log "INFO" "🚀 Running React/Node.js fix..."
    if bash "$react_fix_script"; then
        record_fix_result "React/Node.js" "SUCCESS"
        return 0
    else
        record_fix_result "React/Node.js" "FAILED"
        return 1
    fi
}

# System validation
validate_system() {
    log "STEP" "🧪 System Validation"
    echo ""
    
    local validation_passed=true
    
    # Check MongoDB
    log "INFO" "🔍 Validating MongoDB..."
    if command -v mongod >/dev/null 2>&1; then
        log "SUCCESS" "   ✅ MongoDB binary available"
    else
        log "ERROR" "   ❌ MongoDB binary not found"
        validation_passed=false
    fi
    
    # Check Node.js
    log "INFO" "🔍 Validating Node.js..."
    if command -v node >/dev/null 2>&1; then
        local node_version=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$node_version" -ge 18 ]; then
            log "SUCCESS" "   ✅ Node.js v$(node --version) (compatible)"
        else
            log "ERROR" "   ❌ Node.js version too old: $(node --version)"
            validation_passed=false
        fi
    else
        log "ERROR" "   ❌ Node.js not found"
        validation_passed=false
    fi
    
    # Check React project
    log "INFO" "🔍 Validating React project..."
    if [ -f "$PROJECT_DIR/ui/package.json" ]; then
        cd "$PROJECT_DIR/ui"
        if [ -d "node_modules" ] && [ -f "package-lock.json" ]; then
            log "SUCCESS" "   ✅ React dependencies installed"
        else
            log "WARN" "   ⚠️ React dependencies may need reinstallation"
        fi
    else
        log "ERROR" "   ❌ React project not found"
        validation_passed=false
    fi
    
    # Check Mistral AI files
    log "INFO" "🔍 Validating Mistral AI files..."
    if [ -f "$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py" ]; then
        if grep -q "_determine_optimal_quantization" "$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"; then
            log "SUCCESS" "   ✅ Mistral quantization fix applied"
        else
            log "WARN" "   ⚠️ Mistral quantization fix not detected"
            validation_passed=false
        fi
    else
        log "ERROR" "   ❌ Mistral client file not found"
        validation_passed=false
    fi
    
    if [ "$validation_passed" = true ]; then
        record_fix_result "System Validation" "SUCCESS"
        return 0
    else
        record_fix_result "System Validation" "FAILED"
        return 1
    fi
}

# Show final report
show_final_report() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                      Fix Results Summary                     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Show individual results
    for fix_name in "${!FIX_RESULTS[@]}"; do
        local result="${FIX_RESULTS[$fix_name]}"
        if [ "$result" = "SUCCESS" ]; then
            echo -e "   ✅ ${fix_name}: ${GREEN}SUCCESS${NC}"
        else
            echo -e "   ❌ ${fix_name}: ${RED}FAILED${NC}"
        fi
    done
    
    echo ""
    echo -e "${BLUE}📊 Statistics:${NC}"
    echo "   Total Fixes: $TOTAL_FIXES"
    echo -e "   Successful: ${GREEN}$SUCCESSFUL_FIXES${NC}"
    echo -e "   Failed: ${RED}$FAILED_FIXES${NC}"
    echo ""
    
    if [ $FAILED_FIXES -eq 0 ]; then
        echo -e "${GREEN}🎉 All fixes completed successfully!${NC}"
        echo ""
        echo -e "${YELLOW}🚀 Next Steps:${NC}"
        echo "   1. Test the installation:"
        echo "      ./install_claritygr_new.sh"
        echo ""
        echo "   2. Run specific tests:"
        echo "      • MongoDB: sudo systemctl status mongod"
        echo "      • Mistral: python scripts/test_local_mistral.py"
        echo "      • React: cd ui && npm run dev"
        echo ""
        echo "   3. Access the application:"
        echo "      • Backend: http://localhost:8000"
        echo "      • Frontend: http://localhost:3000"
        echo ""
    else
        echo -e "${RED}⚠️ Some fixes failed - manual intervention may be required${NC}"
        echo ""
        echo -e "${YELLOW}💡 Troubleshooting:${NC}"
        echo "   • Check individual fix logs above"
        echo "   • Run fixes individually for detailed output"
        echo "   • Consult documentation for manual fixes"
        echo ""
    fi
}

# Main function
main() {
    # Show banner and get confirmation
    show_banner
    ask_confirmation
    
    log "INFO" "🚀 Starting comprehensive system fix..."
    
    # Check prerequisites
    if ! check_prerequisites; then
        log "ERROR" "❌ Prerequisites check failed - cannot continue"
        exit 1
    fi
    
    # Run fixes in order
    log "INFO" "🔧 Running fixes in optimal order..."
    echo ""
    
    # Fix 1: MongoDB (must be first as other components depend on it)
    fix_mongodb_corruption
    echo ""
    
    # Fix 2: Mistral AI (independent of others)
    fix_mistral_quantization
    echo ""
    
    # Fix 3: React/Node.js (independent of others)
    fix_react_nodejs
    echo ""
    
    # Validation
    validate_system
    
    # Show final report
    show_final_report
    
    # Exit with appropriate code
    if [ $FAILED_FIXES -eq 0 ]; then
        log "SUCCESS" "🎉 All fixes completed successfully!"
        exit 0
    else
        log "ERROR" "❌ Some fixes failed"
        exit 1
    fi
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 