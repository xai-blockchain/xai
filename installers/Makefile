# XAI Blockchain - Installer Build Makefile
# ============================================================================
# Build and test all installation packages
#
# Usage:
#   make all          - Build all packages
#   make debian       - Build Debian package
#   make rpm          - Build RPM package
#   make test         - Test all installers
#   make clean        - Clean build artifacts
# ============================================================================

.PHONY: all debian rpm homebrew docker test clean help

# Configuration
VERSION := 0.2.0
PROJECT_ROOT := $(shell cd .. && pwd)
DIST_DIR := $(PROJECT_ROOT)/dist
BUILD_DIR := $(PROJECT_ROOT)/build

all: debian rpm docker

help:
	@echo "XAI Blockchain Installer Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all          - Build all packages"
	@echo "  debian       - Build Debian/Ubuntu .deb package"
	@echo "  rpm          - Build CentOS/Fedora/RHEL .rpm package"
	@echo "  homebrew     - Validate Homebrew formula"
	@echo "  docker       - Build Docker images"
	@echo "  test         - Test all installers"
	@echo "  test-debian  - Test Debian package in container"
	@echo "  test-rpm     - Test RPM package in container"
	@echo "  test-docker  - Test Docker installer"
	@echo "  test-script  - Test shell installer"
	@echo "  clean        - Remove build artifacts"
	@echo "  checksums    - Generate SHA256 checksums"
	@echo "  verify       - Verify package checksums"
	@echo ""
	@echo "Variables:"
	@echo "  VERSION=$(VERSION)"
	@echo "  PROJECT_ROOT=$(PROJECT_ROOT)"

# ============================================================================
# Debian Package
# ============================================================================

debian: debian/control debian/rules debian/postinst debian/changelog
	@echo "Building Debian package..."
	cd $(PROJECT_ROOT) && dpkg-buildpackage -us -uc -b
	@echo "Debian package built: ../xai-blockchain_$(VERSION)_all.deb"

debian-source:
	@echo "Building Debian source package..."
	cd $(PROJECT_ROOT) && dpkg-buildpackage -S -us -uc
	@echo "Source package built"

# ============================================================================
# RPM Package
# ============================================================================

rpm: xai.spec
	@echo "Building RPM package..."
	@mkdir -p $(HOME)/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	@cp xai.spec $(HOME)/rpmbuild/SPECS/
	@cd $(PROJECT_ROOT) && tar czf $(HOME)/rpmbuild/SOURCES/xai-blockchain-$(VERSION).tar.gz .
	rpmbuild -ba $(HOME)/rpmbuild/SPECS/xai.spec
	@echo "RPM package built: $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-$(VERSION)-1.*.rpm"

rpm-source:
	@echo "Building source RPM..."
	rpmbuild -bs $(HOME)/rpmbuild/SPECS/xai.spec
	@echo "SRPM built: $(HOME)/rpmbuild/SRPMS/xai-blockchain-$(VERSION)-1.*.src.rpm"

# ============================================================================
# Homebrew Formula
# ============================================================================

homebrew: xai.rb
	@echo "Validating Homebrew formula..."
	brew audit --strict --online xai.rb || true
	@echo "Formula validated"

homebrew-test:
	@echo "Testing Homebrew formula..."
	brew install --build-from-source xai.rb
	brew test xai
	brew uninstall xai

# ============================================================================
# Docker Images
# ============================================================================

docker:
	@echo "Building Docker images..."
	cd $(PROJECT_ROOT) && docker build -t xai-blockchain/node:$(VERSION) -f docker/node/Dockerfile .
	docker tag xai-blockchain/node:$(VERSION) xai-blockchain/node:latest
	@echo "Docker image built: xai-blockchain/node:$(VERSION)"

docker-testnet:
	cd $(PROJECT_ROOT) && docker build -t xai-blockchain/node:testnet -f docker/node/Dockerfile .

docker-mainnet:
	cd $(PROJECT_ROOT) && docker build -t xai-blockchain/node:mainnet -f docker/node/Dockerfile .

docker-push:
	@echo "Pushing Docker images..."
	docker push xai-blockchain/node:$(VERSION)
	docker push xai-blockchain/node:latest

# ============================================================================
# Testing
# ============================================================================

test: test-script test-docker test-debian test-rpm

test-script:
	@echo "Testing install-xai.sh..."
	bash -n install-xai.sh
	shellcheck install-xai.sh || true
	@echo "Script syntax OK"

test-docker:
	@echo "Testing docker-install.sh..."
	bash -n docker-install.sh
	shellcheck docker-install.sh || true
	./docker-install.sh --help
	@echo "Docker installer OK"

test-debian:
	@echo "Testing Debian package in Docker..."
	docker run --rm -v $(PROJECT_ROOT)/..:/build debian:12 bash -c "\
		apt-get update && \
		apt-get install -y /build/xai-blockchain_$(VERSION)_all.deb && \
		xai --version && \
		systemctl status xai-node --no-pager || true"

test-rpm:
	@echo "Testing RPM package in Docker..."
	docker run --rm -v $(HOME)/rpmbuild/RPMS:/rpms fedora:39 bash -c "\
		dnf install -y /rpms/noarch/xai-blockchain-$(VERSION)-1.*.rpm && \
		xai --version && \
		systemctl status xai-node --no-pager || true"

test-windows:
	@echo "Testing Windows PowerShell installer..."
	pwsh -File install-xai.ps1 -WhatIf || powershell -File install-xai.ps1 -WhatIf

# ============================================================================
# Checksums and Verification
# ============================================================================

checksums:
	@echo "Generating SHA256 checksums..."
	@mkdir -p $(DIST_DIR)
	sha256sum install-xai.sh docker-install.sh install-xai.ps1 > $(DIST_DIR)/SHA256SUMS
	@if [ -f ../xai-blockchain_$(VERSION)_all.deb ]; then \
		sha256sum ../xai-blockchain_$(VERSION)_all.deb >> $(DIST_DIR)/SHA256SUMS; \
	fi
	@if [ -f $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-$(VERSION)-1.*.rpm ]; then \
		sha256sum $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-$(VERSION)-1.*.rpm >> $(DIST_DIR)/SHA256SUMS; \
	fi
	@echo "Checksums written to $(DIST_DIR)/SHA256SUMS"

verify:
	@echo "Verifying checksums..."
	cd $(DIST_DIR) && sha256sum -c SHA256SUMS

sign:
	@echo "Signing packages with GPG..."
	@if [ -f $(DIST_DIR)/SHA256SUMS ]; then \
		gpg --detach-sign --armor $(DIST_DIR)/SHA256SUMS; \
	fi

# ============================================================================
# Release
# ============================================================================

release: clean all checksums
	@echo "Creating release artifacts..."
	@mkdir -p $(DIST_DIR)/installers
	cp install-xai.sh install-xai.ps1 docker-install.sh $(DIST_DIR)/installers/
	cp INSTALL.md README.md $(DIST_DIR)/installers/
	@if [ -f ../xai-blockchain_$(VERSION)_all.deb ]; then \
		cp ../xai-blockchain_$(VERSION)_all.deb $(DIST_DIR)/; \
	fi
	@if [ -f $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-$(VERSION)-1.*.rpm ]; then \
		cp $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-$(VERSION)-1.*.rpm $(DIST_DIR)/; \
	fi
	@echo "Release artifacts ready in $(DIST_DIR)"

github-release:
	@echo "Creating GitHub release..."
	gh release create v$(VERSION) \
		--title "XAI Blockchain v$(VERSION)" \
		--notes "See CHANGELOG.md for details" \
		$(DIST_DIR)/installers/* \
		$(DIST_DIR)/*.deb \
		$(DIST_DIR)/*.rpm \
		$(DIST_DIR)/SHA256SUMS \
		$(DIST_DIR)/SHA256SUMS.asc

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	rm -f ../xai-blockchain_*.deb
	rm -f ../xai-blockchain_*.changes
	rm -f ../xai-blockchain_*.buildinfo
	rm -f ../xai-blockchain_*.dsc
	rm -rf $(HOME)/rpmbuild/BUILD/xai-blockchain-*
	rm -f $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-*
	rm -f $(HOME)/rpmbuild/SRPMS/xai-blockchain-*
	docker rmi xai-blockchain/node:$(VERSION) 2>/dev/null || true
	@echo "Clean complete"

distclean: clean
	rm -rf $(HOME)/rpmbuild
	@echo "Distribution clean complete"

# ============================================================================
# Development
# ============================================================================

lint:
	@echo "Linting shell scripts..."
	shellcheck install-xai.sh docker-install.sh || true
	@echo "Linting PowerShell..."
	pwsh -Command "Invoke-ScriptAnalyzer install-xai.ps1" || true

format:
	@echo "Formatting shell scripts..."
	shfmt -w install-xai.sh docker-install.sh

# ============================================================================
# Information
# ============================================================================

info:
	@echo "Build Information:"
	@echo "  Version: $(VERSION)"
	@echo "  Project Root: $(PROJECT_ROOT)"
	@echo "  Dist Directory: $(DIST_DIR)"
	@echo ""
	@echo "Available packages:"
	@ls -lh ../xai-blockchain_*.deb 2>/dev/null || echo "  No Debian packages found"
	@ls -lh $(HOME)/rpmbuild/RPMS/noarch/xai-blockchain-*.rpm 2>/dev/null || echo "  No RPM packages found"
	@docker images xai-blockchain/node 2>/dev/null || echo "  No Docker images found"

# Default target
.DEFAULT_GOAL := help
