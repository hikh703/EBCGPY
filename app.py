from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import io
import os
import zipfile
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import barcode
from barcode.writer import ImageWriter
from flask import send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix  # For compatibility with Vercel

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/generate-labels", methods=["POST", "OPTIONS"])
def generate_labels():
    if request.method == "OPTIONS":
        # Handle preflight request
        return jsonify({"message": "Preflight check"}), 200

    try:
        # Step 1: Retrieve uploaded file and user number
        uploaded_file = request.files.get("file")
        user_number = request.form.get("user_number")
        
        if not uploaded_file or not user_number:
            return jsonify({"error": "File and user number are required"}), 400

        # Step 2: Read Excel file
        df = pd.read_excel(uploaded_file)
        required_columns = {"Nom", "Prix", "Valeur Option1"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            return jsonify({"error": f"Missing required columns: {missing_columns}"}), 400

        # Step 3: Add "Code-barres" column
        today = datetime.now().strftime("%Y%m%d")
        df["Code-barres"] = [
            f"SELEC{today}{user_number}{str(idx).zfill(4)}" for idx in range(len(df))
        ]

        # Step 4: Generate label images
        dpi = 300
        label_width = int(60 * dpi / 25.4)  # 60mm to pixels
        label_height = int(30 * dpi / 25.4)  # 30mm to pixels

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for _, product in df.iterrows():
                # Create blank label
                label = Image.new("RGB", (label_width, label_height), "white")
                draw = ImageDraw.Draw(label)

                # Load custom font (optional)
                try:
                    font_path = "arial.ttf"  # Replace with your font path
                    font_large = ImageFont.truetype(font_path, 42)
                    font_small = ImageFont.truetype(font_path, 32)
                except IOError:
                    font_large = font_small = ImageFont.load_default()

                # Product details
                text_name = product['Nom']
                text_size = f"Taille: {product['Valeur Option1']}"
                text_price = f"{product['Prix']}€"

                # Measure text sizes using textbbox
                text_name_bbox = draw.textbbox((0, 0), text_name, font=font_large)
                text_size_bbox = draw.textbbox((0, 0), text_size, font=font_small)
                text_price_bbox = draw.textbbox((0, 0), text_price, font=font_small)

                text_name_width = text_name_bbox[2] - text_name_bbox[0]
                text_name_height = text_name_bbox[3] - text_name_bbox[1]

                text_size_width = text_size_bbox[2] - text_size_bbox[0]
                text_size_height = text_size_bbox[3] - text_size_bbox[1]

                text_price_width = text_price_bbox[2] - text_price_bbox[0]
                text_price_height = text_price_bbox[3] - text_price_bbox[1]

                # Barcode generation
                barcode_code = product["Code-barres"]
                EAN = barcode.get_barcode_class("code128")
                ean = EAN(barcode_code, writer=ImageWriter())
                barcode_image = ean.render(writer_options={"module_height": 10, "dpi": dpi})

                # Resize barcode
                barcode_width = int(label_width * 0.8)
                barcode_height = int(label_height * 0.4)
                barcode_image = barcode_image.resize((barcode_width, barcode_height), Image.LANCZOS)

                # Total content height
                total_text_height = (
                    text_name_height + text_size_height + text_price_height + (2 * 10)  # Line spacings
                )
                total_content_height = total_text_height + barcode_height + 10  # Space between text and barcode
                y_start = (label_height - total_content_height) // 2  # Centering vertically

                # Draw text
                draw.text(
                    ((label_width - text_name_width) // 2, y_start),
                    text_name,
                    fill="black",
                    font=font_large,
                )
                draw.text(
                    ((label_width - text_size_width) // 2, y_start + text_name_height + 15),
                    text_size,
                    fill="black",
                    font=font_small,
                )
                draw.text(
                    ((label_width - text_price_width) // 2, y_start + text_name_height + text_size_height + 30),
                    text_price,
                    fill="black",
                    font=font_small,
                )

                # Paste barcode
                barcode_x = (label_width - barcode_width) // 2
                barcode_y = y_start + total_text_height + 30
                label.paste(barcode_image, (barcode_x, barcode_y))

                # Save label as PNG in memory
                label_buffer = io.BytesIO()
                label.save(label_buffer, format="PNG")
                label_buffer.seek(0)

                # Add to ZIP
                zf.writestr(f"{barcode_code}_label.png", label_buffer.read())

        zip_buffer.seek(0)

        # Step 5: Return ZIP file
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="labels.zip"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500



import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port, debug=True)
