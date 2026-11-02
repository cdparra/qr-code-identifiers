import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import io
import math

def make_qr_image(data):
    """Helper function to generate a QR code image object in memory."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return ImageReader(img_buffer)

def generate_student_qr_sets(total_students, output_prefix="exam_sets", batch_size=2500):
    """
    Generates 2 columns of student blocks per page.
    Each block contains a PRE qr, POST qr, and an ID card separated by dashed cut-lines.
    """
    # Grid settings: 2 columns, 5 rows = 10 student sets per page
    cols = 2
    rows = 5
    sets_per_page = cols * rows
    
    page_width, page_height = letter
    block_width = 4.0 * inch
    block_height = 2.0 * inch
    
    # Margins to center the 8x10 inch printable area on the page
    margin_x = 0.25 * inch
    margin_y = 0.5 * inch

    # Updated Spanish fields
    fields = ["Nombre:", "Sexo:", "Escuela:", "Grado:", "Ciudad:"]
    
    num_batches = math.ceil(total_students / batch_size)
    current_id = 1
    
    for batch in range(num_batches):
        students_in_batch = min(batch_size, total_students - (batch * batch_size))
        filename = f"{output_prefix}_part{batch + 1}.pdf"
        
        c = canvas.Canvas(filename, pagesize=letter)
        
        for i in range(students_in_batch):
            # Create a new page after every 10 student blocks
            if i > 0 and i % sets_per_page == 0:
                c.showPage()
                
            pos_in_page = i % sets_per_page
            col = pos_in_page % cols
            row = pos_in_page // cols
            
            # (x, y) marks the bottom-left corner of the current 4"x2" student block
            x = margin_x + (col * block_width)
            y = page_height - margin_y - ((row + 1) * block_height)
            
            # --- 1. DRAW DASHED CUT LINES ---
            c.setDash(4, 4) # Pattern: 4 points dashed, 4 points gap
            c.setLineWidth(0.5)
            c.setStrokeColorRGB(0.6, 0.6, 0.6) # Light grey for cut lines
            
            # Outer boundary of the entire block
            c.rect(x, y, block_width, block_height)
            # Divider between PRE (first inch) and POST (second inch)
            c.line(x + 1.0 * inch, y, x + 1.0 * inch, y + block_height)
            # Divider between POST and ID Card (remaining 2 inches)
            c.line(x + 2.0 * inch, y, x + 2.0 * inch, y + block_height)
            
            # Reset to solid, black lines for the write-in fields
            c.setDash() 
            c.setStrokeColorRGB(0, 0, 0)
            
            # --- 2. GENERATE PRE & POST IDs ---
            qr_pre_id = f"EXAM-{current_id:06d}-PRE"
            qr_post_id = f"EXAM-{current_id:06d}-POS"
            
            # --- 3. DRAW PRE-TEST SECTION (Left inch) ---
            img_pre = make_qr_image(qr_pre_id)
            qr_size = 0.8 * inch
            c.drawImage(img_pre, x + 0.1 * inch, y + 0.35 * inch, width=qr_size, height=qr_size)
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 0.15 * inch, y + 1.35 * inch, "PRE-TEST")
            c.setFont("Helvetica", 7)
            c.drawString(x + 0.05 * inch, y + 0.15 * inch, qr_pre_id)
            
            # --- 4. DRAW POST-TEST SECTION (Second inch) ---
            img_post = make_qr_image(qr_post_id)
            c.drawImage(img_post, x + 1.1 * inch, y + 0.35 * inch, width=qr_size, height=qr_size)
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 1.1 * inch, y + 1.35 * inch, "POST-TEST")
            c.setFont("Helvetica", 7)
            c.drawString(x + 1.05 * inch, y + 0.15 * inch, qr_post_id)
            
            # --- 5. DRAW IDENTIFICATION CARD (Right two inches) ---
            text_x = x + 2.1 * inch
            line_end_x = x + block_width - 0.1 * inch
            
            c.setFont("Helvetica-Bold", 9)
            y_offset = y + block_height - 0.25 * inch
            line_spacing = 0.35 * inch # Spaced perfectly for 5 fields
            
            for field in fields:
                c.drawString(text_x, y_offset, field)
                
                word_length = c.stringWidth(field, "Helvetica-Bold", 9)
                line_start_x = text_x + word_length + 3
                
                c.setLineWidth(0.5)
                c.line(line_start_x, y_offset - 1, line_end_x, y_offset - 1)
                
                y_offset -= line_spacing
            
            current_id += 1
            
        c.save()
        print(f"Saved {filename} with {students_in_batch} student sets.")

# Example execution: Generate sets for 10,000 students (which creates 20,000 QR codes total)
# This will generate 4 PDFs of 250 pages each (10 students per page).
generate_student_qr_sets(total_students=10000, batch_size=2500)