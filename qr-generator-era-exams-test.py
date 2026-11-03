import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import math
import pandas as pd
import os

def load_students_from_csv(csv_path, limit):
    """
    Función robusta para leer el CSV, manejando posibles problemas de codificación 
    o encabezados residuales de exportaciones.
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
            "turno": get_col(row, 'turno')
        })
    return students

def generate_exam_kits(usar_csv=True, csv_path="era_nna_exams_2026_consolidado.csv", cantidad=10, id_inicial=100000, output_prefix="exam_kits"):
    
    # 1. Obtener los datos (del CSV o generar vacíos)
    if usar_csv:
        students = load_students_from_csv(csv_path, limit=cantidad)
        total_students = len(students)
        print(f"Cargados {total_students} estudiantes desde el CSV.")
    else:
        students = [None] * cantidad # Lista de nulos para generar tarjetas vacías
        total_students = cantidad
        print(f"Generando {total_students} tarjetas vacías.")
        
    if total_students == 0:
        return

    # Configuración de diseño optimizada para A4: 2 columnas × 5 filas
    cols, rows = 2, 5
    students_per_page = cols * rows
    page_width, page_height = A4
    block_width = 4.0 * inch
    block_height = 2.0 * inch

    # Centrar horizontal y verticalmente el bloque completo en la página A4.
    margin_x = (page_width - (cols * block_width)) / 2
    margin_y = (page_height - (rows * block_height)) / 2

    # Configuración de las 5 secciones de la etiqueta
    w_qr = 0.6 * inch      # Ancho para cada uno de los 4 QRs (2.4" total)
    w_card = 1.6 * inch    # Ancho restante para la tarjeta de ID (1.6" total)
    
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
        ("Turno:", "turno")
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
    c = canvas.Canvas(filename, pagesize=A4)

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
        x = margin_x + (col * block_width)
        y = page_height - margin_y - ((row + 1) * block_height)
        
        # --- LÍNEAS PUNTEADAS DE CORTE ---
        c.saveState()
        c.setDash(2, 2)
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        for j in range(1, 5): # Dibuja 4 líneas separadoras verticales
            line_x = x + (j * w_qr)
            c.line(line_x, y, line_x, y + block_height)
        c.restoreState()
        
        # --- SECCIÓN DE LOS 4 CÓDIGOS QR ---
        for idx, (fase, materia, sufijo) in enumerate(qr_configs):
            qr_x = x + idx * w_qr
            
            # Encabezados (Ej. "PRE" y luego "COM")
            c.setFont("NotoSans-Bold", 7)
            c.drawCentredString(qr_x + w_qr/2, y + block_height - 0.2 * inch, fase)
            c.drawCentredString(qr_x + w_qr/2, y + block_height - 0.35 * inch, materia)
            
            # Imagen QR
            qr_data = f"EXAM-{student_id}{sufijo}"
            qr_size = 0.45 * inch
            qr_img = make_qr_image(qr_data)
            c.drawImage(qr_img, qr_x + (w_qr - qr_size)/2, y + (block_height - qr_size)/2, width=qr_size, height=qr_size)
            
            # Pie (Código base y sufijo)
            c.setFont("NotoSans", 5)
            c.drawCentredString(qr_x + w_qr/2, y + 0.3 * inch, f"EXAM-{student_id}")
            c.drawCentredString(qr_x + w_qr/2, y + 0.15 * inch, sufijo)

        # --- SECCIÓN DE LA TARJETA DE IDENTIFICACIÓN ---
        card_x = x + (4 * w_qr)
        y_offset = y + block_height - 0.25 * inch

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

        y_offset -= 0.38 * inch
        line_spacing = 0.235 * inch

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
# EJECUCIÓN
# ==========================================

# MODO 1: Leer desde el CSV y autocompletar (Generar 10 como prueba)
generate_exam_kits(
    usar_csv=True, 
    csv_path="era_nna_exams_2026_consolidado.csv", 
    cantidad=10, 
    output_prefix="kits_desde_csv"
)

# MODO 2: Generar tarjetas vacías empezando desde el código 200000
# generate_exam_kits(usar_csv=False, cantidad=10, id_inicial=200000, output_prefix="kits_vacios")