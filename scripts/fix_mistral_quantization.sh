#!/bin/bash

# ClarityGR Mistral AI Quantization Fix Script
# Fixes AsyncLocalMistralClient quantization 'auto' error

# Set up logging
log() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message"
}

log "INFO" "🔧 ClarityGR Mistral AI Quantization Fix"
log "INFO" "======================================"

# Main script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

log "INFO" "📂 Project Directory: $PROJECT_DIR"

# Check if running with proper permissions
if [ "$EUID" -eq 0 ]; then
    log "ERROR" "❌ Do not run this script as root"
    log "INFO" "💡 Run as regular user: ./scripts/fix_mistral_quantization.sh"
    exit 1
fi

# Check if AsyncLocalMistralClient exists
check_mistral_files() {
    log "STEP" "🔍 Checking Mistral AI files..."
    
    local async_client_file="$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"
    local base_client_file="$PROJECT_DIR/src/services/base/local_mistral_client.py"
    
    if [ ! -f "$async_client_file" ]; then
        log "ERROR" "❌ AsyncLocalMistralClient not found: $async_client_file"
        return 1
    fi
    
    if [ ! -f "$base_client_file" ]; then
        log "ERROR" "❌ LocalBaseMistralClient not found: $base_client_file"
        return 1
    fi
    
    log "SUCCESS" "✅ Mistral AI client files found"
    return 0
}

# Backup original files
backup_files() {
    log "STEP" "📄 Creating backup of original files..."
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local async_client_file="$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"
    local base_client_file="$PROJECT_DIR/src/services/base/local_mistral_client.py"
    
    # Create backup directory
    local backup_dir="$PROJECT_DIR/backups/mistral_fix_$timestamp"
    mkdir -p "$backup_dir"
    
    # Backup files
    cp "$async_client_file" "$backup_dir/local_mistral_client.py.backup"
    cp "$base_client_file" "$backup_dir/local_mistral_client_base.py.backup"
    
    log "SUCCESS" "✅ Files backed up to: $backup_dir"
}

# Check current quantization issue
check_quantization_issue() {
    log "STEP" "🔍 Checking for quantization issue..."
    
    local async_client_file="$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"
    
    # Check if the issue exists
    if grep -q "self.quantization = os.getenv('MISTRAL_LOCAL_QUANTIZATION', 'none')" "$async_client_file"; then
        log "ERROR" "❌ Found old quantization handling - needs fix"
        return 1
    elif grep -q "_determine_optimal_quantization" "$async_client_file"; then
        log "SUCCESS" "✅ Smart quantization already implemented"
        return 0
    else
        log "WARN" "⚠️ Quantization handling unclear - applying fix anyway"
        return 1
    fi
}

# Apply AsyncLocalMistralClient fix
fix_async_mistral_client() {
    log "STEP" "🔧 Fixing AsyncLocalMistralClient quantization handling..."
    
    local async_client_file="$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"
    
    # Create the fix patch
    cat > "/tmp/mistral_quantization_fix.patch" << 'EOF'
--- a/src/infrastructure/llm/local_mistral_client.py
+++ b/src/infrastructure/llm/local_mistral_client.py
@@ -73,14 +73,46 @@ class AsyncLocalMistralClient:
             logger.error("❌ CUDA not available - GPU is required for this application")
             raise RuntimeError("CUDA GPU is required for local Mistral inference. No CPU fallback allowed.")
         
-        # Read quantization configuration from environment
-        self.quantization = get_setting('mistral_local_quantization', 'none').lower()
+        # Get GPU memory for quantization decisions
+        self.available_gpu_memory_gb = gpu_memory_gb
+        self.required_gpu_memory = 55.0 if gpu_memory_gb >= 30 else 2.0
+        
+        # Read quantization configuration from environment with smart conversion
+        self.quantization = self._determine_optimal_quantization(get_setting)
+            
+    def _determine_optimal_quantization(self, get_setting) -> str:
+        """Convert 'auto' quantization to valid vLLM quantization method"""
+        
+        # Read quantization from settings/environment
+        env_quant = get_setting('mistral_local_quantization', 'auto').lower()
         if hasattr(app_settings, 'mistral_local_quantization'):
-            self.quantization = app_settings.mistral_local_quantization.lower()
+            env_quant = app_settings.mistral_local_quantization.lower()
         elif NER_SETTINGS_AVAILABLE and hasattr(ner_settings, 'mistral_local_quantization'):
-            self.quantization = ner_settings.mistral_local_quantization.lower()
+            env_quant = ner_settings.mistral_local_quantization.lower()
         else:
-            # Fallback to environment variable
             import os
-            self.quantization = os.getenv('MISTRAL_LOCAL_QUANTIZATION', 'none').lower()
+            env_quant = os.getenv('MISTRAL_LOCAL_QUANTIZATION', 'auto').lower()
        
+        # If not auto, use as-is
+        if env_quant != "auto":
+            logger.info(f"🔧 Using environment-specified quantization: {env_quant}")
+            return env_quant
+        
+        # Auto-select based on GPU memory
+        available_memory = self.available_gpu_memory_gb
+        required_memory = self.required_gpu_memory
+        
+        if available_memory >= required_memory * 1.2:  # 20% headroom
+            quantization = "none"
+            logger.info(f"✅ Sufficient memory ({available_memory:.1f}GB) - no quantization needed")
+        elif available_memory >= required_memory * 0.7:  # Can fit with INT8
+            quantization = "bitsandbytes"
+            logger.info(f"🔧 Using INT8 quantization for {available_memory:.1f}GB GPU")
+        else:
+            quantization = "bitsandbytes-nf4"  # Most aggressive
+            logger.info(f"🔧 Using INT4 quantization for {available_memory:.1f}GB GPU")
+        
+        return quantization
             
         self.max_retries = get_setting('mistral_max_retries', 3)
         self.timeout_seconds = get_setting('mistral_timeout', 60)
EOF

    # Apply the patch
    if patch -p1 -d "$PROJECT_DIR" < "/tmp/mistral_quantization_fix.patch"; then
        log "SUCCESS" "✅ AsyncLocalMistralClient quantization fix applied"
    else
        log "WARN" "⚠️ Patch failed, applying manual fix..."
        
        # Manual fix using sed
        sed -i '/# Read quantization configuration from environment/,/self\.quantization = os\.getenv/c\
        # Get GPU memory for quantization decisions\
        self.available_gpu_memory_gb = gpu_memory_gb\
        self.required_gpu_memory = 55.0 if gpu_memory_gb >= 30 else 2.0\
        \
        # Read quantization configuration from environment with smart conversion\
        self.quantization = self._determine_optimal_quantization(get_setting)' "$async_client_file"
        
        # Add the _determine_optimal_quantization method
        sed -i '/logger\.info("💡 Model will be loaded on first inference call (lazy loading)")/a\
\
    def _determine_optimal_quantization(self, get_setting) -> str:\
        """Convert auto quantization to valid vLLM quantization method"""\
        \
        # Read quantization from settings/environment\
        env_quant = get_setting("mistral_local_quantization", "auto").lower()\
        if hasattr(app_settings, "mistral_local_quantization"):\
            env_quant = app_settings.mistral_local_quantization.lower()\
        elif NER_SETTINGS_AVAILABLE and hasattr(ner_settings, "mistral_local_quantization"):\
            env_quant = ner_settings.mistral_local_quantization.lower()\
        else:\
            import os\
            env_quant = os.getenv("MISTRAL_LOCAL_QUANTIZATION", "auto").lower()\
        \
        # If not auto, use as-is\
        if env_quant != "auto":\
            logger.info(f"🔧 Using environment-specified quantization: {env_quant}")\
            return env_quant\
        \
        # Auto-select based on GPU memory\
        available_memory = self.available_gpu_memory_gb\
        required_memory = self.required_gpu_memory\
        \
        if available_memory >= required_memory * 1.2:  # 20% headroom\
            quantization = "none"\
            logger.info(f"✅ Sufficient memory ({available_memory:.1f}GB) - no quantization needed")\
        elif available_memory >= required_memory * 0.7:  # Can fit with INT8\
            quantization = "bitsandbytes"\
            logger.info(f"🔧 Using INT8 quantization for {available_memory:.1f}GB GPU")\
        else:\
            quantization = "bitsandbytes-nf4"  # Most aggressive\
            logger.info(f"🔧 Using INT4 quantization for {available_memory:.1f}GB GPU")\
        \
        return quantization' "$async_client_file"
        
        log "SUCCESS" "✅ Manual quantization fix applied"
    fi
    
    # Clean up temp file
    rm -f "/tmp/mistral_quantization_fix.patch"
}

# Fix vLLM kwargs handling
fix_vllm_kwargs() {
    log "STEP" "🔧 Fixing vLLM kwargs quantization handling..."
    
    local async_client_file="$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"
    
    # Fix the quantization parameter passing to vLLM
    sed -i '/base_kwargs\["quantization"\] = self\.quantization/c\
            # Add quantization configuration if enabled (with proper validation)\
            if self.quantization != "none":\
                if self.quantization in ["bitsandbytes", "bitsandbytes-nf4", "awq", "gptq", "fp8"]:\
                    base_kwargs["quantization"] = self.quantization\
                    if "bitsandbytes" in self.quantization:\
                        base_kwargs["load_format"] = "bitsandbytes"\
                    logger.info(f"🔧 Using {self.quantization} quantization")\
                else:\
                    logger.warning(f"⚠️ Unknown quantization {self.quantization}, skipping quantization")' "$async_client_file"
    
    log "SUCCESS" "✅ vLLM kwargs quantization handling fixed"
}

# Test the fix
test_quantization_fix() {
    log "STEP" "🧪 Testing quantization fix..."
    
    # Test Python syntax
    if python3 -m py_compile "$PROJECT_DIR/src/infrastructure/llm/local_mistral_client.py"; then
        log "SUCCESS" "✅ Python syntax validation passed"
    else
        log "ERROR" "❌ Python syntax validation failed"
        return 1
    fi
    
    # Test imports
    cd "$PROJECT_DIR"
    if python3 -c "
import sys
sys.path.append('src')
try:
    from infrastructure.llm.local_mistral_client import AsyncLocalMistralClient
    print('✅ AsyncLocalMistralClient import successful')
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"; then
        log "SUCCESS" "✅ AsyncLocalMistralClient import test passed"
    else
        log "ERROR" "❌ AsyncLocalMistralClient import test failed"
        return 1
    fi
    
    return 0
}

# Main function
main() {
    log "INFO" "🚀 Starting Mistral AI quantization fix..."
    
    # Step 1: Check files
    if ! check_mistral_files; then
        log "ERROR" "❌ Required files not found"
        return 1
    fi
    
    # Step 2: Check if fix is needed
    if check_quantization_issue; then
        log "SUCCESS" "✅ Quantization fix already applied or not needed"
        return 0
    fi
    
    # Step 3: Backup files
    backup_files
    
    # Step 4: Apply AsyncLocalMistralClient fix
    if ! fix_async_mistral_client; then
        log "ERROR" "❌ Failed to fix AsyncLocalMistralClient"
        return 1
    fi
    
    # Step 5: Fix vLLM kwargs
    fix_vllm_kwargs
    
    # Step 6: Test the fix
    if ! test_quantization_fix; then
        log "ERROR" "❌ Fix validation failed"
        return 1
    fi
    
    # Final status
    log "SUCCESS" "🎉 Mistral AI quantization fix completed successfully!"
    log "INFO" "✅ AsyncLocalMistralClient now properly handles 'auto' quantization"
    log "INFO" "💡 Test with: python scripts/test_local_mistral.py"
    
    return 0
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 