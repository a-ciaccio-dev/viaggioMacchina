"""
Convertitore professionale da Markdown (.md) a PDF con fpdf2.
Include supporto completo per tabelle multi-riga auto-wrappanti (nessuna sovrapposizione),
colori chiari e leggibili, callout decorati, elenchi con rientro, intestazioni curate e font Unicode.
"""
import os
import re
import sys
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

class TripPDF(FPDF):
    def __init__(self, font_family="helvetica", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_font = font_family

    def header(self):
        if self.page_no() > 1:
            self.set_y(8)
            self.set_font(self.custom_font, "I", 8)
            self.set_text_color(130, 145, 165)
            self.set_x(15)
            self.cell(105, 5, "Report di Viaggio: Tolmezzo (UD) -> Montreuil (Francia)", border=0, align="L")
            self.set_x(120)
            self.cell(75, 5, "Trip Cost Calculator", border=0, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(210, 222, 238)
            self.set_line_width(0.3)
            self.line(15, 14.5, 195, 14.5)
            self.set_y(19)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(220, 230, 242)
        self.set_line_width(0.3)
        self.line(15, self.get_y() - 1.5, 195, self.get_y() - 1.5)
        self.set_font(self.custom_font, "", 8)
        self.set_text_color(140, 150, 165)
        self.cell(0, 6, f"Documento di Viaggio e Pianificazione Costi  |  Pagina {self.page_no()}/{{nb}}", border=0, align="C")

def clean_inline(text: str) -> str:
    """Rimuove markdown e caratteri non supportati, gestisce frecce ed entità"""
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = text.replace(r'\rightarrow', '->').replace(r'\leftrightarrow', '<->').replace('$', '')
    text = text.replace('★', ' Stelle ').replace('  Stelle', ' Stelle')
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U00002600-\U000026FF"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    return text.strip()

def setup_fonts(pdf: FPDF) -> str:
    win_fonts = "C:/Windows/Fonts"
    arial_regular = os.path.join(win_fonts, "arial.ttf")
    arial_bold = os.path.join(win_fonts, "arialbd.ttf")
    arial_italic = os.path.join(win_fonts, "ariali.ttf")
    arial_bold_italic = os.path.join(win_fonts, "arialbi.ttf")

    if os.path.exists(arial_regular) and os.path.exists(arial_bold):
        pdf.add_font("ArialUni", style="", fname=arial_regular)
        pdf.add_font("ArialUni", style="B", fname=arial_bold)
        if os.path.exists(arial_italic):
            pdf.add_font("ArialUni", style="I", fname=arial_italic)
        if os.path.exists(arial_bold_italic):
            pdf.add_font("ArialUni", style="BI", fname=arial_bold_italic)
        return "ArialUni"
    return "helvetica"

def determine_col_widths(rows: list) -> tuple:
    num_cols = max(len(r) for r in rows)
    first_row_text = " ".join(rows[0]).lower() if rows else ""
    
    if num_cols == 2:
        return (65.0, 115.0)
    elif num_cols == 3:
        if "voce" in first_row_text or "spesa" in first_row_text or "andata" in first_row_text or "sintesi" in first_row_text:
            # Tabella Sintesi Costi (Voce di Spesa, Sola Andata, Andata e Ritorno)
            return (88.0, 44.0, 48.0)
        return (50.0, 65.0, 65.0)
    elif num_cols == 4:
        if "paese" in first_row_text or "attraversato" in first_row_text:
            # Tabella Prezzi Carburante per Paese:
            # Paese (28mm) | Prezzo Autostrada (46mm) | Prezzo Minimo / Smart (66mm) | Risparmio al Litro (40mm)
            return (28.0, 46.0, 66.0, 40.0)
        elif "scenario" in first_row_text or "rifornimento" in first_row_text:
            # Tabella Confronto Scenari:
            # Scenario (68mm) | Prezzo Medio (34mm) | Sola Andata (38mm) | Andata e Ritorno (40mm)
            return (68.0, 34.0, 38.0, 40.0)
        elif "parcheggio" in first_row_text or "soluzione" in first_row_text or "vantaggi" in first_row_text:
            # Tabella Parcheggi Montreuil:
            # Soluzione (38mm) | Tipologia (32mm) | Costo Stimato (30mm) | Vantaggi e Svantaggi (80mm)
            return (38.0, 32.0, 30.0, 80.0)
        return (45.0, 45.0, 45.0, 45.0)
    elif num_cols == 5:
        if "progressiv" in first_row_text or "svolta" in first_row_text:
            return (52.0, 48.0, 26.0, 26.0, 28.0)
        elif "hotel" in first_row_text or "struttura" in first_row_text or "camera" in first_row_text:
            return (44.0, 36.0, 30.0, 26.0, 44.0)
        # Tabella pedaggi (Tratta, Tipologia, Costo Andata, Costo Ritorno, Totale A/R)
        return (46.0, 48.0, 28.0, 28.0, 30.0)
    elif num_cols == 6:
        if "discrepanz" in first_row_text or "verifica" in first_row_text or "delta" in first_row_text:
            return (35.0, 24.0, 24.0, 20.0, 35.0, 42.0)
        # Tabella Punti di Svolta / Tappe (Tratta Da->A, Autostrada/Dir., Distanza Tratta, Km Prog., Tempo Tratta, Tempo Prog.)
        return (38.0, 42.0, 25.0, 25.0, 24.0, 26.0)
    else:
        w = 180.0 / num_cols
        return tuple(w for _ in range(num_cols))

def render_table_block(pdf: FPDF, rows: list, font_name: str):
    if not rows:
        return

    # Garanzia che nessuna tabella venga spezzata tra due pagine
    space_left = pdf.h - pdf.b_margin - pdf.get_y()
    if space_left < 50:
        pdf.add_page()

    # Reset dello stato grafico
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(51, 65, 85)
    pdf.set_draw_color(210, 220, 235)
    pdf.set_line_width(0.2)
    pdf.set_font(font_name, "", 8.0)

    col_widths = determine_col_widths(rows)
    first_row_text = " ".join(rows[0]).lower() if rows else ""
    
    # Determina allineamento coerente per colonna
    num_cols = len(col_widths)
    col_alignments = ["L"] * num_cols
    
    if num_cols == 6:
        col_alignments = ["L", "L", "C", "C", "C", "C"]
    elif num_cols == 5:
        col_alignments = ["L", "L", "C", "C", "C"]
    elif num_cols == 4:
        if "paese" in first_row_text:
            col_alignments = ["L", "C", "L", "C"]
        elif "scenario" in first_row_text:
            col_alignments = ["L", "C", "C", "C"]
        elif "parcheggio" in first_row_text or "soluzione" in first_row_text:
            col_alignments = ["L", "L", "C", "L"]
    elif num_cols == 3:
        col_alignments = ["L", "C", "C"]

    headings_style = FontFace(
        family=font_name,
        emphasis="B",
        size_pt=8.0,
        color=(15, 35, 75),
        fill_color=(233, 242, 254)  # Azzurrino chiaro per l'intestazione
    )

    bold_style = FontFace(emphasis="B")

    with pdf.table(
        col_widths=col_widths,
        first_row_as_headings=True,
        headings_style=headings_style,
        cell_fill_mode="ROWS",
        cell_fill_color=(247, 249, 253),  # Grigio-azzurro chiarissimo per le righe alternate
        padding=1.6,
        line_height=4.0,
        width=180
    ) as table:
        for r_idx, row in enumerate(rows):
            t_row = table.row()
            row_raw_text = " ".join(row).lower()
            is_summary_row = ("totale" in row_raw_text or "risparmio" in row_raw_text or "quota" in row_raw_text)
            
            for c_idx, cell_value in enumerate(row):
                m = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', cell_value)
                link_url = m.group(2) if m else None
                val = clean_inline(cell_value)
                align = col_alignments[c_idx] if c_idx < len(col_alignments) else "L"
                
                # Grassetto per righe di riepilogo o celle con enfasi **
                cell_is_bold = ("**" in cell_value) or (is_summary_row and r_idx > 0)
                style = bold_style if cell_is_bold else None
                
                if r_idx == 0:
                    t_row.cell(val, align=align)
                else:
                    if link_url:
                        t_row.cell(val, align=align, link=link_url, style=style)
                    else:
                        t_row.cell(val, align=align, style=style)

    # Ripristino post tabella
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(51, 65, 85)
    pdf.ln(3)

def render_callout_block(pdf: FPDF, lines: list, font_name: str):
    """Renderizza un box callout decorato con sfondo azzurro chiaro e barra laterale blu"""
    if not lines:
        return
    text = " ".join(clean_inline(l.lstrip("> ")) for l in lines)
    
    pdf.set_font(font_name, "", 8.5)
    lines_count = len(pdf.multi_cell(170, 4.1, text, dry_run=True, output="LINES"))
    box_height = (lines_count * 4.1) + 4.0

    start_y = pdf.get_y()
    if (pdf.h - pdf.b_margin - start_y) < (box_height + 4):
        pdf.add_page()
        start_y = pdf.get_y()

    # 1. Disegna sfondo rettangolo chiaro
    pdf.set_fill_color(243, 247, 254)  # Azzurro perla chiarissimo
    pdf.set_draw_color(219, 234, 254)  # Bordo azzurro chiaro
    pdf.set_line_width(0.3)
    pdf.rect(15, start_y, 180, box_height, style="FD")

    # 2. Disegna barra d'accento laterale blu
    pdf.set_fill_color(37, 99, 235)    # Blu vivace
    pdf.rect(15, start_y, 2.5, box_height, style="F")

    # 3. Scrive il testo sopra lo sfondo
    pdf.set_xy(20.5, start_y + 2.0)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(172, 4.1, text, border=0, align="L")
    
    # 4. Reset post callout
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(51, 65, 85)
    pdf.set_y(start_y + box_height + 2.5)

def convert_md_to_pdf(md_path: str, pdf_path: str):
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"File non trovato: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        raw_lines = [line.rstrip("\r\n") for line in f.readlines()]

    temp_pdf = FPDF()
    font_name = setup_fonts(temp_pdf)

    pdf = TripPDF(font_family=font_name, orientation="P", unit="mm", format="A4")
    setup_fonts(pdf)
    pdf.alias_nb_pages()
    pdf.set_margins(15, 19, 15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Inizializzazione stato grafico sicuro
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(51, 65, 85)
    pdf.set_draw_color(226, 232, 240)

    i = 0
    table_rows = []
    callout_lines = []

    while i < len(raw_lines):
        line = raw_lines[i].strip()

        # 1. Riconoscimento Tabelle Markdown
        if line.startswith("|") and line.endswith("|"):
            if re.match(r'^\|[\s\:\-\|]+\|$', line):
                i += 1
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        elif table_rows:
            render_table_block(pdf, table_rows, font_name)
            table_rows = []

        # 2. Riconoscimento Callout (> ...)
        if line.startswith(">"):
            callout_lines.append(line)
            i += 1
            continue
        elif callout_lines:
            render_callout_block(pdf, callout_lines, font_name)
            callout_lines = []

        if not line:
            pdf.ln(1.5)
            i += 1
            continue

        # 3. Linea Divisoria (---)
        if line.startswith("---"):
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            curr_y = pdf.get_y()
            pdf.line(15, curr_y + 1, 195, curr_y + 1)
            pdf.ln(3.5)
            i += 1
            continue

        # 4. Titolo Principale (# ) - Banner di Testata
        if line.startswith("# "):
            title_text = clean_inline(line[2:])
            banner_height = 20
            start_y = pdf.get_y()
            
            # Sfondo banner
            pdf.set_fill_color(15, 23, 42) # Slate 900
            pdf.rect(15, start_y, 180, banner_height, style="F")
            
            # Testo titolo
            pdf.set_xy(18, start_y + 3.8)
            pdf.set_font(font_name, "B", 13.5)
            pdf.set_text_color(248, 250, 252)
            pdf.cell(174, 6, title_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            # Sottotitolo
            pdf.set_xy(18, start_y + 11.2)
            pdf.set_font(font_name, "", 8.5)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(174, 5, "Itinerario Ottimizzato  *  Consumi, Pedaggi e Parcheggi  *  Trip Cost Calculator", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            # Reset stato grafico subito dopo il banner!
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(51, 65, 85)
            pdf.set_y(start_y + banner_height + 4)
            i += 1
            continue

        # 5. Titoli Sezione (## )
        if line.startswith("## "):
            # Sezioni importanti o con tabelle estese iniziano a pagina nuova per garantire perfetta leggibilità
            is_new_page_section = any(line.startswith(prefix) for prefix in ["## 3.", "## 4.", "## 5.", "## 6.", "## 7.", "## 8."])
            if is_new_page_section or (pdf.h - pdf.b_margin - pdf.get_y()) < 65:
                pdf.add_page()
            else:
                pdf.ln(2)

            h2_text = clean_inline(line[3:])
            pdf.set_font(font_name, "B", 11)
            pdf.set_text_color(30, 58, 138)
            pdf.cell(0, 6, h2_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_draw_color(59, 130, 246)
            pdf.set_line_width(0.4)
            line_y = pdf.get_y()
            pdf.line(15, line_y, 195, line_y)
            pdf.ln(2.5)
            
            pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(51, 65, 85)
            i += 1
            continue

        # 6. Sotto-titoli (### )
        if line.startswith("### "):
            # Se è una sottosezione con tabella dedicata (es. Report Verifica Prezzi) o se resta pochissimo spazio per il titolo, va a pagina nuova
            is_sub_new_page = "verifica" in line.lower() or (pdf.h - pdf.b_margin - pdf.get_y()) < 35
            if is_sub_new_page:
                pdf.add_page()
            else:
                pdf.ln(1.5)
            h3_text = clean_inline(line[4:])
            pdf.set_font(font_name, "B", 9.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(0, 5, h3_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1)
            i += 1
            continue

        # 7. Elenchi Puntati o Checkbox
        if line.startswith(("- ", "* ")) or re.match(r'^\d+\.\s', line):
            pdf.set_font(font_name, "", 9)
            pdf.set_text_color(51, 65, 85)
            
            if "- [ ]" in line:
                raw_c = line.replace("- [ ]", "").strip()
                prefix = "[  ] "
            else:
                prefix = "-  " if line.startswith(("- ", "* ")) else f"{line.split('.')[0]}. "
                raw_c = re.sub(r'^(?:[\-\*]|\d+\.)\s*', '', line)

            m = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', raw_c)
            link_url = m.group(2) if m else None
            content = clean_inline(raw_c)

            pdf.set_x(18)
            if link_url:
                pdf.multi_cell(177, 4.2, f"{prefix}{content}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, link=link_url)
            else:
                pdf.multi_cell(177, 4.2, f"{prefix}{content}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.8)
            i += 1
            continue

        # 8. Paragrafo Normale
        pdf.set_font(font_name, "", 9)
        pdf.set_text_color(51, 65, 85)
        cleaned = clean_inline(line)
        pdf.set_x(15)
        pdf.multi_cell(180, 4.3, cleaned, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.2)
        i += 1

    # Chiusura blocchi pendenti a fine file
    if table_rows:
        render_table_block(pdf, table_rows, font_name)
    if callout_lines:
        render_callout_block(pdf, callout_lines, font_name)

    os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
    pdf.output(pdf_path)
    print(f"[OK] PDF generato con successo: {pdf_path}")

if __name__ == "__main__":
    default_md = os.path.join("percorsi", "Tolmezzo_Montreuil", "report_viaggio.md")
    default_pdf = os.path.join("percorsi", "Tolmezzo_Montreuil", "report_viaggio.pdf")
    
    source = sys.argv[1] if len(sys.argv) > 1 else default_md
    target = sys.argv[2] if len(sys.argv) > 2 else default_pdf
    
    convert_md_to_pdf(source, target)
