# Econom'IA 2026 — Beamer slides
#
# Generated data files are produced by `make figures` in the parent directory.
# slides.tex reads them via \addplot table and \InputIfFileExists.

GENERATED := inputs/generated

.PHONY: all clean

all: slides.pdf

slides.pdf: slides.tex $(wildcard $(GENERATED)/*.csv) $(wildcard $(GENERATED)/*.tex)
	tectonic $<

clean:
	rm -f slides.pdf *.aux *.log *.nav *.out *.snm *.toc
