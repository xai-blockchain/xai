# Makefile for Blockchain Project Documentation

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
MKDOCS        = mkdocs
PDOC          = pdoc3

# Default target
.DEFAULT_GOAL := help

# Put it first so that "make" without argument is like "make help".
help:
	@echo "Blockchain Project Documentation Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  make html           - Build HTML documentation using Sphinx"
	@echo "  make mkdocs         - Build HTML documentation using MkDocs"
	@echo "  make serve          - Serve MkDocs documentation locally"
	@echo "  make pdf            - Build PDF documentation"
	@echo "  make epub           - Build EPUB documentation"
	@echo "  make api            - Generate API documentation with pdoc3"
	@echo "  make all            - Build all documentation formats"
	@echo "  make clean          - Remove all build artifacts"
	@echo "  make clean-all      - Remove all build artifacts and caches"
	@echo "  make check          - Check documentation for errors"
	@echo "  make linkcheck      - Check external links"
	@echo "  make deploy         - Deploy documentation to GitHub Pages"
	@echo ""

# Sphinx targets
html:
	@echo "Building HTML documentation with Sphinx..."
	$(SPHINXBUILD) -b html $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html
	@echo ""
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html"

pdf:
	@echo "Building PDF documentation..."
	$(SPHINXBUILD) -b latex $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/latex
	@cd $(BUILDDIR)/latex && $(MAKE) all-pdf
	@echo ""
	@echo "Build finished. The PDF file is in $(BUILDDIR)/latex"

epub:
	@echo "Building EPUB documentation..."
	$(SPHINXBUILD) -b epub $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/epub
	@echo ""
	@echo "Build finished. The EPUB file is in $(BUILDDIR)/epub"

man:
	@echo "Building man pages..."
	$(SPHINXBUILD) -b man $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/man
	@echo ""
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man"

singlehtml:
	@echo "Building single HTML page..."
	$(SPHINXBUILD) -b singlehtml $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/singlehtml
	@echo ""
	@echo "Build finished. The single HTML page is in $(BUILDDIR)/singlehtml"

# MkDocs targets
mkdocs:
	@echo "Building documentation with MkDocs..."
	cd .. && $(MKDOCS) build
	@echo ""
	@echo "Build finished. The HTML pages are in site/"

serve:
	@echo "Serving documentation locally..."
	@echo "Navigate to http://127.0.0.1:8000"
	cd .. && $(MKDOCS) serve

deploy:
	@echo "Deploying documentation to GitHub Pages..."
	cd .. && $(MKDOCS) gh-deploy --clean --message "Update documentation [ci skip]"
	@echo ""
	@echo "Documentation deployed successfully!"

# API documentation with pdoc3
api:
	@echo "Generating API documentation with pdoc3..."
	$(PDOC) --html --output-dir $(BUILDDIR)/api --force ../src
	@echo ""
	@echo "Build finished. API documentation is in $(BUILDDIR)/api"

# Quality checks
check:
	@echo "Checking documentation for errors..."
	$(SPHINXBUILD) -b dummy $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/dummy
	@echo ""
	@echo "Documentation check complete!"

linkcheck:
	@echo "Checking external links..."
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/linkcheck
	@echo ""
	@echo "Link check complete! See $(BUILDDIR)/linkcheck/output.txt"

spelling:
	@echo "Checking spelling..."
	$(SPHINXBUILD) -b spelling $(SPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/spelling
	@echo ""
	@echo "Spelling check complete!"

# Build all formats
all: clean html mkdocs pdf api
	@echo ""
	@echo "All documentation formats built successfully!"

# Clean targets
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILDDIR)/*
	cd .. && rm -rf site/
	@echo "Clean complete!"

clean-all: clean
	@echo "Cleaning all caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Deep clean complete!"

# Live reload for development
watch:
	@echo "Starting live reload server..."
	sphinx-autobuild $(SOURCEDIR) $(BUILDDIR)/html

# Create requirements file for documentation
requirements:
	@echo "Generating documentation requirements..."
	@echo "# Documentation Build Requirements" > requirements-docs.txt
	@echo "sphinx>=8.0.0" >> requirements-docs.txt
	@echo "sphinx-rtd-theme>=3.0.0" >> requirements-docs.txt
	@echo "mkdocs>=1.6.0" >> requirements-docs.txt
	@echo "mkdocs-material>=9.7.0" >> requirements-docs.txt
	@echo "pdoc3>=0.11.0" >> requirements-docs.txt
	@echo "sphinx-autobuild>=2024.0.0" >> requirements-docs.txt
	@echo "" >> requirements-docs.txt
	@echo "Requirements file generated: requirements-docs.txt"

# Statistics
stats:
	@echo "Documentation Statistics:"
	@echo "========================="
	@echo ""
	@echo "Markdown files:"
	@find . -name "*.md" -type f | wc -l
	@echo ""
	@echo "ReStructuredText files:"
	@find . -name "*.rst" -type f | wc -l
	@echo ""
	@echo "Total lines of documentation:"
	@find . -name "*.md" -o -name "*.rst" | xargs wc -l | tail -1
	@echo ""

# Validation
validate:
	@echo "Validating documentation structure..."
	@test -f index.md || echo "Warning: index.md not found"
	@test -d architecture || echo "Warning: architecture/ directory not found"
	@test -d api || echo "Warning: api/ directory not found"
	@test -d deployment || echo "Warning: deployment/ directory not found"
	@test -d security || echo "Warning: security/ directory not found"
	@test -d user-guides || echo "Warning: user-guides/ directory not found"
	@echo "Validation complete!"

# Open documentation in browser
open:
	@echo "Opening documentation in browser..."
	@if [ -f $(BUILDDIR)/html/index.html ]; then \
		python -m webbrowser $(BUILDDIR)/html/index.html; \
	else \
		echo "HTML documentation not found. Run 'make html' first."; \
	fi

# Create tarball for distribution
dist:
	@echo "Creating documentation distribution..."
	@make clean
	@make all
	@tar -czf blockchain-docs-$(shell date +%Y%m%d).tar.gz $(BUILDDIR)/
	@echo "Distribution created: blockchain-docs-$(shell date +%Y%m%d).tar.gz"

.PHONY: help html pdf epub man singlehtml mkdocs serve deploy api check linkcheck spelling all clean clean-all watch requirements stats validate open dist
