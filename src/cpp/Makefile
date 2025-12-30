# DeadDrop Cryptography Module - Emscripten Build Configuration
#
# Prerequisites:
#   - Emscripten SDK (emsdk) installed and activated
#   - Run: source /path/to/emsdk/emsdk_env.sh
#
# Usage:
#   make        # Build WASM module
#   make clean  # Remove build artifacts

EMCC = emcc
EMFLAGS = -O3 \
          -std=c++20 \
          -s WASM=1 \
          -s EXPORTED_FUNCTIONS='["_encrypt_file","_decrypt_file","_malloc","_free"]' \
          -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap","HEAP8"]' \
          -s ALLOW_MEMORY_GROWTH=1 \
          -s INITIAL_MEMORY=67108864 \
          -s MAXIMUM_MEMORY=134217728 \
          -s MODULARIZE=1 \
          -s EXPORT_NAME='createCryptoModule' \
          -s ENVIRONMENT='web' \
          -s FILESYSTEM=0 \
          -s ASSERTIONS=0 \
          -s MALLOC='emmalloc' \
          --no-entry

OUTPUT_DIR = ../web/public
OUTPUT = $(OUTPUT_DIR)/crypto.js

all: $(OUTPUT)

$(OUTPUT): crypto.cpp monocypher.c monocypher.h
	@echo "Building WASM cryptography module..."
	@mkdir -p $(OUTPUT_DIR)
	$(EMCC) $(EMFLAGS) crypto.cpp monocypher.c -o $(OUTPUT)
	@echo "✓ WASM module compiled to $(OUTPUT)"
	@echo "✓ Generated files: crypto.js, crypto.wasm"

clean:
	@echo "Cleaning build artifacts..."
	@rm -f $(OUTPUT_DIR)/crypto.js $(OUTPUT_DIR)/crypto.wasm
	@echo "✓ Clean complete"

.PHONY: all clean
