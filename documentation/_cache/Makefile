# Makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
PAPER         =
SRCDIR        = source
BUILDDIR      = ..
PYTHON        = python3

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/build/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) $(SRCDIR)

.PHONY: help clean html web pickle htmlhelp latex changes linkcheck api

default: html

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html        standalone HTML files"
	@echo "  html_noapi  same as above, without the time consuming API docs"
	@echo "  pickle      pickle files (usable by e.g. sphinx-web)"
	@echo "  htmlhelp    HTML files and a HTML help project"
	@echo "  latex       LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  texinfo     Texinfo files"
	@echo "  info        Texinfo files and run them through makeinfo"
	@echo "  changes     an overview over all changed/added/deprecated items"
	@echo "  linkcheck   check all external links for integrity (takes a long time)"
	@echo
	@echo "Compound utility targets:"
	@echo "pdf          latex and then runs the PDF generation"
	@echo "all          html and pdf"
	@echo "dist         all, and then puts the results in dist/"

clean_api:
	-rm -rf $(SRCDIR)/api/generated

clean: clean_api
	-rm -rf $(BUILDDIR)/build/* $(BUILDDIR)/dist/*
	-rm -f $(SRCDIR)/config/options/config-generated.txt

pdf: latex
	cd $(BUILDDIR)/build/latex && make all-pdf

all: html pdf

# For final distribution, only build HTML (our pdf is now so large as to be
# unusable, takes forever to build and just bloats the downloads).  We leave
# them hardlinked at the top-level so users find them easily, though the
# original build/html dir is left in-place (useful to reload builds while
# testing).
dist: html
	rm -rf $(BUILDDIR)/html
	cp -al $(BUILDDIR)/build/html .
	@echo "Build finished.  Final docs are in html/"

html: api autoconfig
html_noapi: clean_api autoconfig

html html_noapi:
	mkdir -p $(BUILDDIR)/build/html $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/build/html
	@echo
	@echo "Build finished. The HTML pages are in build/html."

autoconfig: source/config/options/config-generated.txt

source/config/options/config-generated.txt: autogen_config.py
	$(PYTHON) autogen_config.py
	@echo "Created docs for config options"

api: source/api/generated/gen.txt

source/api/generated/gen.txt:
	$(PYTHON) autogen_api.py
	@echo "Build API docs finished."

pickle:
	mkdir -p $(BUILDDIR)/build/pickle $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b pickle $(ALLSPHINXOPTS) $(BUILDDIR)/build/pickle
	@echo
	@echo "Build finished; now you can process the pickle files or run"
	@echo "  sphinx-web build/pickle"
	@echo "to start the sphinx-web server."

web: pickle

htmlhelp:
	mkdir -p $(BUILDDIR)/build/htmlhelp $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) $(BUILDDIR)/build/htmlhelp
	@echo
	@echo "Build finished; now you can run HTML Help Workshop with the" \
	      ".hhp project file in build/htmlhelp."

latex: api autoconfig
	mkdir -p $(BUILDDIR)/build/latex $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) $(BUILDDIR)/build/latex
	@echo
	@echo "Build finished; the LaTeX files are in build/latex."
	@echo "Run \`make all-pdf' or \`make all-ps' in that directory to" \
	      "run these through (pdf)latex."

changes:
	mkdir -p $(BUILDDIR)/build/changes $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b changes $(ALLSPHINXOPTS) $(BUILDDIR)/build/changes
	@echo
	@echo "The overview file is in build/changes."

linkcheck:
	mkdir -p $(BUILDDIR)/build/linkcheck $(BUILDDIR)/build/doctrees
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) $(BUILDDIR)/build/linkcheck
	@echo
	@echo "Link check complete; look for any errors in the above output " \
	      "or in build/linkcheck/output.rst."

texinfo:
	mkdir -p $(BUILDDIR)/texinfo
	$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) $(BUILDDIR)/texinfo
	@echo
	@echo "Build finished. The Texinfo files are in $(BUILDDIR)/texinfo."
	@echo "Run \`make' in that directory to run these through makeinfo" \
	      "(use \`make info' here to do that automatically)."

info:
	mkdir -p $(BUILDDIR)/texinfo
	$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) $(BUILDDIR)/texinfo
	@echo "Running Texinfo files through makeinfo..."
	make -C $(BUILDDIR)/texinfo info
	@echo "makeinfo finished; the Info files are in $(BUILDDIR)/texinfo."
