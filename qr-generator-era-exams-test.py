import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import math
import argparse
import pandas as pd
import os

def load_students_from_csv(csv_path, limit):
    """
    Función para leer el CSV, gestionando problemas de codificación o encabezados 
    residuales de exportaciones.
    """
    if not os.path.exists(csv_path):
        print(f"Error: No se encontró el archivo {csv_path}")
        return []
        
    try:
        # Prefer UTF-8, then support legacy Windows exports commonly encoded as CP1252/Latin-1.
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, sep=',', encoding='cp1252', on_bad_lines='skip')
        except Exception:
            df = pd.read_csv(csv_path, sep=',', encoding='latin-1', on_bad_lines='skip')

    df.columns = df.columns.str.strip().str.lower()
    
    def get_col(row, col_name):
        return str(row[col_name]).strip() if col_name in row and pd.notna(row[col_name]) else ""

    students = []
    # Agrupamos por id_nna para asegurar que tomamos una sola tarjeta por estudiante
    if 'id_nna' in df.columns:
        grouped = df.groupby('id_nna').first().reset_index()
    else:
        grouped = df

    for _, row in grouped.head(limit).iterrows():
        students.append({
            "id": get_col(row, 'id_nna'),
            "nombre": get_col(row, 'nombre_apellido'),
            "sexo": get_col(row, 'sexo').upper()[:1], # F o M
            "distrito": get_col(row, 'distrito'),
            "escuela": get_col(row, 'escuela_nro'),
            "grado": get_col(row, 'grado'),
            "turno": get_col(row, 'turno'),
            "nivel": get_col(row, 'nivel'),
            "facilitador": get_col(row, 'facilitador')
        })
    return students

def get_page_layout(orientacion="portrait", tamano_pagina="A4"):
    """Calcula dinámicamente la cuadrícula según orientación y tamaño de hoja."""
    orientacion = orientacion.lower()
    tamano_pagina = tamano_pagina.upper()

    formatos = {"A4": A4, "LETTER": letter}
    if tamano_pagina not in formatos:
        raise ValueError("El tamaño de página debe ser 'A4' o 'Letter'.")

    base_width, base_height = formatos[tamano_pagina]
    if orientacion in ("portrait", "retrato"):
        page_size = (base_width, base_height)
    elif orientacion in ("landscape", "horizontal"):
        page_size = landscape(formatos[tamano_pagina])
    else:
        raise ValueError("La orientación debe ser 'portrait' o 'landscape'.")

    page_width, page_height = page_size
    margin = 12
    minimum_card_width = 3.0 * inch
    preferred_card_width = 4.0 * inch
    preferred_card_height = 2.0 * inch
    minimum_card_height = 1.75 * inch

    max_cols = max(1, int((page_width - 2 * margin) // minimum_card_width))
    row_minimum = minimum_card_height if orientacion in ("landscape", "horizontal") else preferred_card_height
    max_rows = max(1, int((page_height - 2 * margin) // row_minimum))

    best_layout = None
    best_capacity = 0
    for cols in range(1, max_cols + 1):
        for rows in range(1, max_rows + 1):
            block_width = min(preferred_card_width, (page_width - 2 * margin) / cols)
            block_height = min(preferred_card_height, (page_height - 2 * margin) / rows)
            if block_width < minimum_card_width or block_height < minimum_card_height:
                continue

            capacity = cols * rows
            if capacity > best_capacity:
                best_capacity = capacity
                best_layout = (cols, rows, block_width, block_height)

    if best_layout is None:
        return page_size, 1, 1, preferred_card_width, preferred_card_height

    cols, rows, block_width, block_height = best_layout
    return page_size, cols, rows, block_width, block_height


def dividir_elementos(elementos, cantidad_archivos):
    """Divide una lista en partes equilibradas sin perder ni duplicar elementos."""
    if cantidad_archivos < 1:
        raise ValueError("La cantidad de archivos debe ser mayor que cero.")

    base, sobrantes = divmod(len(elementos), cantidad_archivos)
    grupos = []
    inicio = 0
    for indice in range(cantidad_archivos):
        longitud = base + (1 if indice < sobrantes else 0)
        grupos.append(elementos[inicio:inicio + longitud])
        inicio += longitud
    return grupos


def generate_exam_kits(usar_csv=True, csv_path="era_nna_exams_2026_consolidado.csv", cantidad=10,
                       id_inicial=100000, output_prefix="exam_kits", orientacion="portrait",
                       tamano_pagina="A4", cantidad_archivos=1, _datos_estudiantes=None):
    
    # 1. Obtener los datos (del CSV o generar vacíos)
    if _datos_estudiantes is not None:
        students = _datos_estudiantes
        total_students = len(students)
    elif usar_csv:
        students = load_students_from_csv(csv_path, limit=cantidad)
        total_students = len(students)
        print(f"Cargados {total_students} estudiantes desde el CSV.")
    else:
        students = [None] * cantidad # Lista de nulos para generar tarjetas vacías
        total_students = cantidad
        print(f"Generando {total_students} tarjetas vacías.")

    if total_students == 0:
        return

    if cantidad_archivos < 1:
        raise ValueError("La cantidad de archivos debe ser mayor que cero.")

    if cantidad_archivos > 1 and _datos_estudiantes is None:
        grupos = dividir_elementos(students, cantidad_archivos)
        inicio_id = 0
        for indice, grupo in enumerate(grupos, start=1):
            if not grupo:
                continue
            nombre_parte = f"{output_prefix}_{indice}_de_{cantidad_archivos}"
            generate_exam_kits(
                usar_csv=False,
                cantidad=len(grupo),
                id_inicial=id_inicial + inicio_id,
                output_prefix=nombre_parte,
                orientacion=orientacion,
                tamano_pagina=tamano_pagina,
                cantidad_archivos=1,
                _datos_estudiantes=grupo
            )
            inicio_id += len(grupo)
        return

    # Configuración de diseño optimizada para cada orientación A4.
    page_size, cols, rows, block_width, block_height = get_page_layout(orientacion, tamano_pagina)
    students_per_page = cols * rows
    page_width, page_height = page_size

    # Separación uniforme entre tarjetas; los espacios dejan las líneas de corte legibles.
    card_gap_x = 0.08 * inch
    card_gap_y = 0.08 * inch
    card_width = block_width - card_gap_x
    card_height = block_height - card_gap_y

    # Centrar horizontal y verticalmente todos los bloques, incluyendo los espacios.
    margin_x = (page_width - (cols * card_width + (cols - 1) * card_gap_x)) / 2
    margin_y = (page_height - (rows * card_height + (rows - 1) * card_gap_y)) / 2

    # Configuración de las 5 secciones de la etiqueta
    w_qr = card_width * 0.15  # 15% para cada uno de los 4 QRs
    w_card = card_width * 0.40  # 40% para la tarjeta de identificación
    
    qr_configs = [
        ("PRE", "COM", "-PRE-COM"),
        ("PRE", "MAT", "-PRE-MAT"),
        ("POS", "COM", "-POS-COM"),
        ("POS", "MAT", "-POS-MAT")
    ]
    
    fields_to_draw = [
        ("F   M", "sexo"),
        ("Distrito:", "distrito"),
        ("Nro. Esc:", "escuela"),
        ("Grado:", "grado"),
        ("Turno:", "turno"),
        ("Nivel:", "nivel"),
        ("Facilitador:", "facilitador")

    ]

    def make_qr_image(data):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return ImageReader(img_buffer)

    filename = f"{output_prefix}.pdf"
    c = canvas.Canvas(filename, pagesize=page_size)

    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    regular_font = os.path.join(font_dir, "NotoSans-Regular.ttf")
    bold_font = os.path.join(font_dir, "NotoSans-Bold.ttf")

    if not os.path.isfile(regular_font) or not os.path.isfile(bold_font):
        raise FileNotFoundError(
            "No se encontraron las fuentes Noto Sans. Mantenga la carpeta 'fonts' "
            "junto al archivo qr-generator-era-exams-test.py."
        )

    pdfmetrics.registerFont(TTFont("NotoSans", regular_font))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", bold_font))
    
    for i in range(total_students):
        student_data = students[i]
        student_id = student_data["id"] if student_data else str(id_inicial + i)
        
        if i > 0 and i % students_per_page == 0:
            c.showPage()
            
        pos_in_page = i % students_per_page
        col = pos_in_page % cols
        row = pos_in_page // cols
        
        # Coordenada (x, y) de la esquina inferior izquierda de la tarjeta completa del estudiante
        x = margin_x + (col * (card_width + card_gap_x))
        y = page_height - margin_y - ((row + 1) * (card_height + card_gap_y)) + card_gap_y
        
        # --- LÍNEAS PUNTEADAS DE CORTE ---
        c.saveState()
        c.setDash(2, 2)
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.rect(x, y, card_width, card_height)
        for j in range(1, 5): # Dibuja 4 líneas separadoras verticales
            line_x = x + (j * w_qr)
            c.line(line_x, y, line_x, y + card_height)
        c.restoreState()
        
        # --- SECCIÓN DE LOS 4 CÓDIGOS QR ---
        for idx, (fase, materia, sufijo) in enumerate(qr_configs):
            qr_x = x + idx * w_qr
            
            # Encabezados (Ej. "PRE" y luego "COM")
            c.setFont("NotoSans-Bold", 7)
            c.drawCentredString(qr_x + w_qr/2, y + card_height - 0.2 * inch, fase)
            c.drawCentredString(qr_x + w_qr/2, y + card_height - 0.35 * inch, materia)
            
            # Imagen QR
            qr_data = f"EXAM-{student_id}{sufijo}"
            qr_size = 0.45 * inch
            qr_img = make_qr_image(qr_data)
            c.drawImage(qr_img, qr_x + (w_qr - qr_size)/2, y + (card_height - qr_size)/2, width=qr_size, height=qr_size)
            
            # Pie (Código base y sufijo)
            c.setFont("NotoSans", 5)
            c.drawCentredString(qr_x + w_qr/2, y + 0.3 * inch, f"EXAM-{student_id}")
            c.drawCentredString(qr_x + w_qr/2, y + 0.15 * inch, sufijo)

        # --- SECCIÓN DE LA TARJETA DE IDENTIFICACIÓN ---
        card_x = x + (4 * w_qr)
        y_offset = y + card_height - 0.25 * inch

        # Nombre: etiqueta arriba y valor en una fila independiente debajo.
        c.setFont("NotoSans-Bold", 7)
        c.drawString(card_x + 0.05 * inch, y_offset, "Nombre:")
        name_y = y_offset - 0.14 * inch
        name_x = card_x + 0.05 * inch
        if student_data and student_data["nombre"]:
            c.setFont("NotoSans", 6.5)
            name_text = str(student_data["nombre"])
            c.drawString(name_x, name_y, name_text[:30])
        else:
            c.setLineWidth(0.5)
            c.line(name_x, name_y - 1, card_x + w_card - 0.05 * inch, name_y - 1)

        y_offset -= 0.34 * inch
        line_spacing = 0.205 * inch

        for label_text, data_key in fields_to_draw:
            c.setFont("NotoSans-Bold", 7)
            
            # Caso especial para "F  M" sin etiqueta de "Sexo:"
            if label_text == "F   M":
                f_x = card_x + 0.1 * inch
                m_x = card_x + 0.4 * inch
                c.drawString(f_x, y_offset, "F")
                c.drawString(m_x, y_offset, "M")
                
                # Si tenemos CSV, marcamos con un círculo la opción correcta
                if student_data and data_key in student_data:
                    sex_val = student_data[data_key]
                    if sex_val == "F":
                        c.circle(f_x + 2.5, y_offset + 2.5, 6) # Círculo sobre la F
                    elif sex_val == "M":
                        c.circle(m_x + 3.0, y_offset + 2.5, 6) # Círculo sobre la M
            else:
                c.drawString(card_x + 0.05 * inch, y_offset, label_text)
                label_w = c.stringWidth(label_text, "NotoSans-Bold", 7)
                val_x = card_x + 0.05 * inch + label_w + 3
                
                # Si hay datos en CSV, imprimirlos
                if student_data and data_key in student_data and student_data[data_key]:
                    c.setFont("NotoSans", 7)
                    # Truncamos el texto a 20 caracteres para que no desborde el ancho de la tarjeta
                    text_val = str(student_data[data_key])[:20] 
                    c.drawString(val_x, y_offset, text_val)
                # Si no hay datos (CSV vacío), dibujar la línea para escribir
                else:
                    c.setLineWidth(0.5)
                    c.line(val_x, y_offset - 1, card_x + w_card - 0.05 * inch, y_offset - 1)
                    
            y_offset -= line_spacing

    c.save()
    print(f"PDF generado exitosamente en: {filename}")

# ==========================================
# EJECUCIÓN POR TERMINAL
# ==========================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera kits de examen con códigos QR e identificación de estudiantes."
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--csv",
        action="store_true",
        help="Leer los datos desde un CSV (modo predeterminado)."
    )
    mode.add_argument(
        "--sin-csv",
        action="store_true",
        help="Generar tarjetas vacías sin datos de estudiantes."
    )

    parser.add_argument(
        "--csv-path",
        default="era_nna_exams_2026_consolidado.csv",
        help="Ruta del archivo CSV."
    )
    parser.add_argument(
        "--cantidad",
        type=int,
        default=10,
        help="Cantidad de kits a generar (predeterminada: 10)."
    )
    parser.add_argument(
        "--id-inicial",
        type=int,
        default=100000,
        help="Primer identificador para tarjetas sin CSV (predeterminado: 100000)."
    )
    parser.add_argument(
        "--output-prefix",
        default="kits_desde_csv",
        help="Nombre base del PDF generado."
    )
    parser.add_argument(
        "--orientacion", "--orientation",
        dest="orientacion",
        choices=("portrait", "landscape"),
        default="portrait",
        help="Orientación de la página: portrait o landscape (predeterminada: portrait)."
    )
    parser.add_argument(
        "--tamano-pagina", "--page-size",
        dest="tamano_pagina",
        choices=("A4", "letter"),
        default="A4",
        help="Tamaño de la hoja: A4 o Letter (predeterminado: A4)."
    )
    parser.add_argument(
        "--cantidad-archivos", "--file-count",
        dest="cantidad_archivos",
        type=int,
        default=1,
        help="Cantidad de archivos PDF entre los que se distribuyen las tarjetas (predeterminado: 1)."
    )

    args = parser.parse_args()
    if args.cantidad < 1:
        parser.error("--cantidad debe ser mayor que cero")
    if args.cantidad_archivos < 1:
        parser.error("--cantidad-archivos debe ser mayor que cero")
    return args


if __name__ == "__main__":
    args = parse_args()

    if args.sin_csv:
        generate_exam_kits(
            usar_csv=False,
            cantidad=args.cantidad,
            id_inicial=args.id_inicial,
            output_prefix=args.output_prefix,
            orientacion=args.orientacion,
            tamano_pagina=args.tamano_pagina,
            cantidad_archivos=args.cantidad_archivos
        )
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = args.csv_path
        if not os.path.isabs(csv_path):
            script_csv_path = os.path.join(script_dir, csv_path)
            if os.path.isfile(script_csv_path):
                csv_path = script_csv_path

        generate_exam_kits(
            usar_csv=True,
            csv_path=csv_path,
            cantidad=args.cantidad,
            id_inicial=args.id_inicial,
            output_prefix=args.output_prefix,
            orientacion=args.orientacion,
            tamano_pagina=args.tamano_pagina,
            cantidad_archivos=args.cantidad_archivos
        )