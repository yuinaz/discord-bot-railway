#!/bin/bash
echo "📦 Membuat virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "📥 Menginstall dependensi..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Instalasi selesai. Jalankan bot dengan:"
echo "source venv/bin/activate && python main.py"