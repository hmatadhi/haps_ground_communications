from pathlib import Path

p = Path(r'C:\Github\haps_ground_communications\HAPS_AI_HW_ChannelModel.tex')
text = p.read_text(encoding='utf-8')
text = text.replace(
    '\\setlength{\\abovecaptionskip}{18pt plus 2pt minus 2pt}\n\\setlength{\\belowcaptionskip}{10pt plus 1pt minus 1pt}\n\\setlength{\\textfloatsep}{14pt plus 2pt minus 2pt}\n',
    '\\setlength{\\abovecaptionskip}{8pt plus 1pt minus 1pt}\n\\setlength{\\belowcaptionskip}{4pt plus 1pt minus 1pt}\n\\setlength{\\textfloatsep}{8pt plus 1pt minus 1pt}\n\\setlength{\\floatsep}{6pt plus 1pt minus 1pt}\n\\setlength{\\intextsep}{6pt plus 1pt minus 1pt}\n\\setlength{\\parskip}{0pt}\n\\setlength{\\parsep}{0pt}\n\\setlength{\\topsep}{2pt}\n\\setlength{\\itemsep}{2pt}\n'
)
for pat in ['\\vspace{2mm}', '\\vspace{3mm}', '\\vspace{3pt}', '\\newpage']:
    text = text.replace(pat, '')
lines = text.splitlines()
out = []
prev_blank = False
for line in lines:
    if line.strip() == '' and prev_blank:
        continue
    out.append(line)
    prev_blank = (line.strip() == '')
text = '\n'.join(out) + '\n'
p.write_text(text, encoding='utf-8')
print('updated', p)
