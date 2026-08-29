LATEX ?= pdflatex
TARGET ?= HAPS_AI_HW_ChannelModel
PDF = $(TARGET).pdf

ifeq ($(OS),Windows_NT)
	RM = del /f /q
else
	RM = rm -f
endif

.PHONY: paper clean

paper: $(PDF)

$(PDF): $(TARGET).tex
	$(LATEX) -interaction=nonstopmode $(TARGET).tex
	$(LATEX) -interaction=nonstopmode $(TARGET).tex

clean:
	$(RM) $(TARGET).aux $(TARGET).log $(TARGET).out $(TARGET).pdf 2>NUL || true
