import os
import json
import base64
import hashlib
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

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


PROMPT = """
You are an expert medical claims and insurance AI auditor and validator.
Analyze these TWO images provided very carefully:
- Image 1: Medical Invoice
- Image 2: Medical Report

CRITICAL EXTRACTION RULES:
- Read the text literally from the images. DO NOT guess, fabricate, or assume any values.
- If a value is genuinely not present in the documents, return null for that field.
  Never invent a plausible-looking value.
- For TotalAmount, extract ONLY the final grand total including VAT (the "Total" /
  "الإجمالي" line). Return it as a plain number with a decimal point, no currency symbol,
  no thousands separators and no extra text. Example: "1725.00".
  Never add the subtotal and the VAT together into one string.
- For HospitalName, use the NAME OF THE FACILITY THAT ISSUED THE INVOICE, which appears
  in the letterhead at the very top of the invoice next to the address, phone number and
  VAT registration number. This is NOT the value of the "Provider" / "مقدم الخدمة" row.
  Example: if the letterhead reads "FMH Alnuzha - Fakeeh Medical Home" and the Provider
  row reads "Al Noor Dental Polyclinic", then HospitalName is "Fakeeh Medical Home"
  and ProviderName is "Al Noor Dental Polyclinic".
- For ProviderName, use the value of the "Provider" / "مقدم الخدمة" row.
- For ClaimId, look for fields like "رقم المطالبة" or "Claim ID" (e.g., CLM-003).
- For MemberId, look for fields like "رقم العضوية" or "Member ID".
- For NationalId, look strictly at the value next to "الهوية الوطنية" or "Nationality ID".
- For InvoiceNumber, extract the exact invoice code.
- For InsuranceCompany, use the "Company Group" / "المجموع" value (e.g. Tawuniya).
- For PolicyNumber, use the number that follows "#" in the "Company" / "اسم الشركة" row.
- For ClaimType, use the "Claim Type" / "نوع المطالبة" value (e.g. Dental).
- For Department, use the "Clinic" / "العيادة" value (e.g. Prosthodontics).
- For ServiceDate, use the "Service Date" / "تاريخ الخدمة" value.
- For Currency, return the ISO 4217 code of the currency the invoice is billed in
  (SAR, USD, AED, EGP, KWD, ...). Saudi invoices normally show "SAR", "SR", "ر.س"
  or "﷼" — all of these are "SAR". If no currency appears anywhere, return "SAR".
- ReportPatientName, ReportDiagnosisCode and ReportDate must be read FROM THE MEDICAL
  REPORT (image 2), not from the invoice, so the two documents can be compared. If the
  report does not state one of them, return null for it.

Perform the following tasks:

1. Document Type Check:
   - Image 1 MUST be an invoice: it has an invoice number, priced line items and a total.
     If Image 1 is a medical report or any other document, set "is_valid": false, explain
     it in "validation_message", and DO NOT take amounts from Image 2.
   - Image 2 MUST be a medical report. If it is not, set "is_valid": false and explain.

2. Data Extraction: extract every field listed in the "data" object below.

3. Clinical Analysis: write "ClinicalSummary" (2-3 sentences describing the patient's
   condition and the treatment performed) and "CoverageHint" (one sentence on how this
   type of treatment is typically handled under insurance coverage).

4. Cross-Validation (MOST IMPORTANT): compare the invoice against the medical report
   field by field. Check at minimum: PatientName, ClaimId, MemberId, NationalId,
   DiagnosisCode, provider/facility, and the service date.
   - For every field that does NOT match, add an object to "discrepancies" with:
     {"field": "...", "invoice_value": "...", "report_value": "...", "severity": "high"|"low"}
   - severity "high" = identity, claim or diagnosis mismatch (a different patient, a
     different claim id, a different diagnosis code, a different national ID).
   - severity "low" = spelling variants of the same name, equivalent date formats,
     or abbreviations of the same facility.
   - Set "match_status" to "success" when there are no discrepancies, "warning" when only
     low-severity ones exist, and "rejected" when any high-severity one exists.
   - If the two documents clearly belong to two different claims, also set
     "is_valid": false.

5. Document Relationship: decide whether the invoice and the medical report describe the
   SAME clinical case. Fill "document_relation":
   - "invoice_specialty": the medical area the invoice bills for (e.g. Dentistry).
   - "report_specialty": the medical area the report documents (e.g. Ophthalmology).
   - "same_clinical_case": true only when the treatment billed on the invoice is the
     treatment described in the report. A dental invoice paired with an eye report is
     false. Different visit dates for the same condition are still true.
   - "reason": one sentence explaining the decision.

6. Confidence: set "confidence" to an integer 0-100 reflecting how clearly you could read
   the documents. Lower it when text is blurry, cropped or partially unreadable.

Return a strict JSON format with this exact structure (Return ONLY valid JSON, no markdown blocks):
{
  "is_valid": true,
  "validation_message": null,
  "match_status": "success",
  "confidence": 95,
  "discrepancies": [
    {"field": "...", "invoice_value": "...", "report_value": "...", "severity": "low"}
  ],
  "document_relation": {
    "invoice_specialty": "...",
    "report_specialty": "...",
    "same_clinical_case": true,
    "reason": "..."
  },
  "clinical_analysis": {
    "ClinicalSummary": "...",
    "CoverageHint": "..."
  },
  "data": {
    "ClaimId": "...",
    "MemberId": "...",
    "NationalId": "...",
    "PatientName": "...",
    "InvoiceNumber": "...",
    "InvoiceDate": "...",
    "ServiceDate": "...",
    "HospitalName": "...",
    "ProviderName": "...",
    "Department": "...",
    "ClaimType": "...",
    "InsuranceCompany": "...",
    "PolicyNumber": "...",
    "DiagnosisCode": "...",
    "DiagnosisDescription": "...",
    "DoctorName": "...",
    "TotalAmount": "...",
    "Currency": "SAR",
    "ReportPatientName": "...",
    "ReportDiagnosisCode": "...",
    "ReportDate": "..."
  }
}
"""


async def analyze_claim(invoice: UploadFile, report: UploadFile):
    # تعريف العميل هنا يضمن قراءة الـ API Key بشكل صحيح بدون أخطاء
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        print(f"📄 Processing Claim - Invoice: {invoice.filename}, Report: {report.filename}")

        invoice_contents = await invoice.read()
        report_contents = await report.read()

        if not invoice_contents or not report_contents:
            raise HTTPException(status_code=400, detail="One of the uploaded files is empty.")

        # حارس: نفس الملف في الخانتين يعني الفاتورة ما وصلت أصلاً، والنتيجة
        # بتطلع أرقام التقرير بدل أرقام الفاتورة بدون أي خطأ ظاهر.
        if hashlib.sha256(invoice_contents).digest() == hashlib.sha256(report_contents).digest():
            raise HTTPException(
                status_code=400,
                detail="The invoice and the medical report are the same file. "
                       "Please upload the invoice in the invoice field."
            )

        message_content = [{"type": "text", "text": PROMPT}]
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
            response_format={"type": "json_object"},
            temperature=0
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

    except HTTPException:
        # بدون هذا السطر كل أخطاء 400 المقصودة فوق تنقلب لـ 500 برسالة غامضة
        raise
    except Exception as e:
        print(f"❌ OpenAI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))