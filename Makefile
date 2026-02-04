# AEDIST Technical Report
# ======================

.PHONY: all tables clean cleaner

all: report.pdf

tables:
	cd aedist/src && python tables.py

report.pdf: report.tex refs.bib
	tectonic $<

# Intermediate files
clean:
	rm -f *.log *.bbl *.blg *.run.xml report.synctex.gz

# Also the output
cleaner: clean
	rm -f report.pdf
