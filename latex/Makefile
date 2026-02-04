# AEDIST Technical Report
# ======================

.PHONY: all tables clean cleaner

all: report.pdf

tables:
	cd ../aedist/src && python tables.py

report.pdf: report.tex refs.bib
	tectonic $<

clean:
	rm -f *.bbl *.blg *.run.xml
	
cleaner: clean
	rm -f report.pdf
