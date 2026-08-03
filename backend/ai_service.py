import os
from dotenv import load_dotenv

load_dotenv()  # This loads the variables from your .env file
import os
import json
import base64
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

from openai import OpenAI

client = OpenAI(api_key="sk-proj-YOUR_ACTUAL_FULL_KEY_WITHOUT_THE_WORD_HERE")
load_dotenv()

app = FastAPI(title="Claim Readiness Platform - OpenAI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# حماية بسيطة من ملفات PDF كبيرة جدًا قبل إرسالها للـ OpenAI
MAX_PDF_PAGES = 10
PDF_RENDER_ZOOM = 2.0  # يقارب 144 DPI، كافٍ لقراءة النصوص بوضوح


def _is_pdf(content_type, filename, content_bytes):
    if (content_type or "").lower() == "application/pdf":
        return True
    if (filename or "").lower().endswith(".pdf"):
        return True
    return content_bytes[:5] == b"%PDF-"


def _pdf_to_data_urls(pdf_bytes):
    """يحوّل كل صفحة من ملف PDF إلى صورة PNG مُرمّزة base64."""
    data_urls = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=400,
                detail=f"PDF has too many pages ({doc.page_count}). Maximum allowed is {MAX_PDF_PAGES}."
            )

        matrix = fitz.Matrix(PDF_RENDER_ZOOM, PDF_RENDER_ZOOM)
        for page in doc:
            pixmap = page.get_pixmap(matrix=matrix)
            png_bytes = pixmap.tobytes("png")
            data_urls.append(f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}")
    finally:
        doc.close()

    return data_urls


def _file_to_data_urls(content_bytes, content_type, filename):
    """يرجع قائمة data URLs: عنصر واحد للصور، وعنصر لكل صفحة لو كان الملف PDF."""
    if _is_pdf(content_type, filename, content_bytes):
        return _pdf_to_data_urls(content_bytes)

    mime = content_type or "image/jpeg"
    return [f"data:{mime};base64,{base64.b64encode(content_bytes).decode('utf-8')}"]


def _append_document_content(content, label, content_bytes, content_type, filename):
    """يضيف نص الوصف وصور المستند (صفحة واحدة أو أكثر) لقائمة محتوى الرسالة."""
    data_urls = _file_to_data_urls(content_bytes, content_type, filename)

    if len(data_urls) == 1:
        content.append({"type": "text", "text": label})
        content.append({"type": "image_url", "image_url": {"url": data_urls[0]}})
    else:
        base_label = label[:-1] if label.endswith(":") else label
        for index, url in enumerate(data_urls, start=1):
            content.append({"type": "text", "text": f"{base_label} (page {index} of {len(data_urls)}):"})
            content.append({"type": "image_url", "image_url": {"url": url}})


async def analyze_claim(invoice: UploadFile, report: UploadFile):
    # تعريف العميل هنا يضمن قراءة الـ API Key بشكل صحيح بدون أخطاء
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    try:
        print(f"📄 Processing Claim - Invoice: {invoice.filename}, Report: {report.filename}")

        invoice_contents = await invoice.read()
        report_contents = await report.read()

        prompt = """
        You are an expert medical claims and insurance AI auditor and validator.
        Analyze these TWO images provided very carefully:
        - Image 1: Medical Invoice
        - Image 2: Medical Report

        CRITICAL EXTRACTION RULES:
        - Read the text literally from the images. DO NOT guess, fabricate, or assume any values.
        - For TotalAmount, extract the final total including VAT.
        - For MemberId, look for fields like "Member ID".
        - For NationalId, look for 10-digit IDs.
        - For InvoiceNumber, extract the exact invoice code.

        Perform the following tasks:
        1. Validity Check: Set "is_valid": true if valid, or false with a reason in "validation_message".
        2. Data Extraction: Extract the 10 required fields: MemberId, NationalId, PatientName, InvoiceNumber, InvoiceDate, HospitalName, DiagnosisCode, DiagnosisDescription, DoctorName, TotalAmount.
        3. Advanced Clinical Analysis: Provide "ClinicalSummary" and "CoverageHint".
        4. Cross-Validation: Check for critical discrepancies in "discrepancies" array and set "match_status" to "success" or "warning"/"rejected".
        
        Return a strict JSON format with this exact structure (Return ONLY valid JSON, no markdown blocks):
        {
          "is_valid": true,
          "validation_message": null,
          "match_status": "success", 
          "discrepancies": [],
          "clinical_analysis": {
            "ClinicalSummary": "...",
            "CoverageHint": "..."
          },
          "data": {
            "MemberId": "...",
            "NationalId": "...",
            "PatientName": "...",
            "InvoiceNumber": "...",
            "InvoiceDate": "...",
            "HospitalName": "...",
            "DiagnosisCode": "...",
            "DiagnosisDescription": "...",
            "DoctorName": "...",
            "TotalAmount": "..."
          }
        }
        """

        message_content = [{"type": "text", "text": prompt}]
        _append_document_content(
            message_content, "This is the Medical Invoice:",
            invoice_contents, invoice.content_type, invoice.filename
        )
        _append_document_content(
            message_content, "This is the Medical Report:",
            report_contents, report.content_type, report.filename
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": message_content
                }
            ],
            response_format={"type": "json_object"}
        )

        result_content = json.loads(response.choices[0].message.content)
        print("✅ Enhanced Pipeline Executed Successfully:", result_content)

        return {
            "status": "success",
            "filenames": {
                "invoice": invoice.filename,
                "report": report.filename
            },
            **result_content
        }

    except Exception as e:
        print(f"❌ OpenAI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))