"""Очистка метаданных и скрытых данных из документов."""

from __future__ import annotations

import io
import zipfile
import xml.etree.ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
EP_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

# Пути к частям метаданных в DOCX
CORE_PROPS = "docProps/core.xml"
APP_PROPS = "docProps/app.xml"
CUSTOM_PROPS = "docProps/custom.xml"

# Метаданные для очистки в core.xml
CORE_FIELDS_TO_CLEAN = [
    ("dc:creator", "Anonymized"),
    ("cp:lastModifiedBy", "Anonymized"),
    ("dc:title", ""),
    ("dc:subject", ""),
    ("dc:description", ""),
    ("cp:keywords", ""),
    ("cp:category", ""),
    ("cp:contentStatus", ""),
    ("cp:version", ""),
    ("cp:revision", "1"),
]

# Метаданные для очистки в app.xml
APP_FIELDS_TO_CLEAN = [
    "Company",
    "Manager",
    "Author",
    "LastAuthor",
    "Template",
    "Comments",
    "HyperlinkBase",
]


def clean_docx_metadata(data: bytes) -> bytes:
    """
    Очищает метаданные из DOCX файла.
    Возвращает новый DOCX с очищенными метаданными.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            replaced = {}
            
            # Копируем все файлы как есть
            for name in names:
                replaced[name] = zf.read(name)
            
            # Очищаем core.xml
            if CORE_PROPS in replaced:
                raw = replaced[CORE_PROPS].decode("utf-8")
                root = ET.fromstring(raw)
                
                # Удаляем или заменяем поля
                for field_name, replacement in CORE_FIELDS_TO_CLEAN:
                    # Ищем элемент с любым namespace
                    for elem in root.iter():
                        tag = elem.tag
                        if field_name in tag or tag.endswith(field_name.split(":")[-1]):
                            if replacement:
                                elem.text = replacement
                            else:
                                elem.text = ""
                
                replaced[CORE_PROPS] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            
            # Очищаем app.xml
            if APP_PROPS in replaced:
                raw = replaced[APP_PROPS].decode("utf-8")
                root = ET.fromstring(raw)
                
                for field_name in APP_FIELDS_TO_CLEAN:
                    for elem in root.iter():
                        tag = elem.tag
                        if field_name in tag or tag.endswith(field_name):
                            elem.text = ""
                
                replaced[APP_PROPS] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            
            # Удаляем custom.xml если есть
            if CUSTOM_PROPS in replaced:
                del replaced[CUSTOM_PROPS]
            
            # Пересобираем ZIP
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as new_zf:
                for name, content in replaced.items():
                    new_zf.writestr(name, content)
            
            return output.getvalue()
    
    except Exception as e:
        print(f"⚠️ Ошибка очистки метаданных DOCX: {e}")
        return data  # Возвращаем оригинал при ошибке


def clean_pdf_metadata(data: bytes) -> bytes:
    """
    Очищает метаданные из PDF файла.
    Возвращает новый PDF с очищенными метаданными.
    """
    try:
        import pymupdf
        
        doc = pymupdf.open(stream=data, filetype="pdf")
        
        # Очищаем метаданные
        doc.set_metadata({
            "title": "",
            "author": "",
            "subject": "",
            "keywords": "",
            "creator": "",
            "producer": "Incognito Anonymizer",
            "creationDate": "",
            "modDate": "",
        })
        
        # Сохраняем
        output = io.BytesIO()
        doc.save(output)
        doc.close()
        
        return output.getvalue()
    
    except Exception as e:
        print(f"⚠️ Ошибка очистки метаданных PDF: {e}")
        return data  # Возвращаем оригинал при ошибке


def clean_xlsx_metadata(data: bytes) -> bytes:
    """
    Очищает метаданные из XLSX файла (docProps/core.xml и app.xml).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            replaced = {}
            for name in names:
                replaced[name] = zf.read(name)

            # Очищаем core.xml — автор, редактор, заголовок и др.
            if CORE_PROPS in replaced:
                raw = replaced[CORE_PROPS].decode("utf-8")
                root = ET.fromstring(raw)

                for field_name, replacement in CORE_FIELDS_TO_CLEAN:
                    for elem in root.iter():
                        tag = elem.tag
                        if field_name in tag or tag.endswith(field_name.split(":")[-1]):
                            elem.text = replacement

                replaced[CORE_PROPS] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

            # Очищаем app.xml — компания, менеджер
            if APP_PROPS in replaced:
                raw = replaced[APP_PROPS].decode("utf-8")
                root = ET.fromstring(raw)

                for field_name in APP_FIELDS_TO_CLEAN:
                    for elem in root.iter():
                        tag = elem.tag
                        if field_name in tag or tag.endswith(field_name):
                            elem.text = ""

                replaced[APP_PROPS] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

            # Удаляем custom.xml если есть
            if CUSTOM_PROPS in replaced:
                del replaced[CUSTOM_PROPS]

            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as new_zf:
                for name, content in replaced.items():
                    new_zf.writestr(name, content)

            return output.getvalue()

    except Exception as e:
        print(f"⚠️ Ошибка очистки метаданных XLSX: {e}")
        return data


def clean_metadata(data: bytes, filename: str) -> bytes:
    """
    Универсальная функция очистки метаданных.
    Определяет тип файла по содержимому (ZIP-подпись), а не по расширению,
    чтобы корректно обрабатывать .doc, .docx и .xlsx.
    """
    # Определяем по магической сигнатуре
    if data[:2] == b"PK":
        # ZIP-архив — проверяем содержимое
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = zf.namelist()
                if any(n.startswith("xl/") for n in names):
                    return clean_xlsx_metadata(data)
                else:
                    return clean_docx_metadata(data)
        except Exception:
            return data  # битый ZIP — не трогаем
    elif data[:5] == b"%PDF-":
        return clean_pdf_metadata(data)
    else:
        return data  # неопознанный формат
