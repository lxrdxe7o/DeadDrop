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
EMXX = em++
COMMONFLAGS = -O3 \
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
MONOCYPHER_OBJ = /tmp/monocypher.o
CRYPTO_OBJ = /tmp/crypto.o

all: $(OUTPUT)

$(MONOCYPHER_OBJ): monocypher.c monocypher.h
	@echo "Compiling monocypher.c (C)..."
	$(EMCC) -O3 -c monocypher.c -o $(MONOCYPHER_OBJ)

$(CRYPTO_OBJ): crypto.cpp monocypher.h
	@echo "Compiling crypto.cpp (C++)..."
	$(EMXX) -O3 -std=c++20 -c crypto.cpp -o $(CRYPTO_OBJ)

$(OUTPUT): $(MONOCYPHER_OBJ) $(CRYPTO_OBJ)
	@echo "Linking WASM module..."
	@mkdir -p $(OUTPUT_DIR)
	$(EMXX) $(COMMONFLAGS) $(MONOCYPHER_OBJ) $(CRYPTO_OBJ) -o $(OUTPUT)
	@echo "✓ WASM module compiled to $(OUTPUT)"
	@echo "✓ Generated files: crypto.js, crypto.wasm"

clean:
	@echo "Cleaning build artifacts..."
	@rm -f $(OUTPUT_DIR)/crypto.js $(OUTPUT_DIR)/crypto.wasm $(MONOCYPHER_OBJ) $(CRYPTO_OBJ)
	@echo "✓ Clean complete"

.PHONY: all clean
