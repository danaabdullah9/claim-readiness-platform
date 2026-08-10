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
You are given one or more documents belonging to a single reimbursement claim.
They may arrive in any order and there may be one, two or several of them.

FIRST, classify every document you are shown into exactly one of:
  "Invoice"        — has an invoice number, priced line items and a total
  "Medical Report" — describes the patient's condition, diagnosis and treatment
  "Prescription"   — lists dispensed medication
  "Other"          — anything else (referral, lab result, receipt, ID copy)

A single document can serve more than one role: some clinics issue one page that
is both an itemised invoice and a clinical report. When that happens, say so in
"combined_document": true and classify it as "Invoice".

THEN extract the claim data from whichever documents contain it. Do not assume a
field lives in a particular document — read all of them.

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
- ReportPatientName, ReportDiagnosisCode and ReportDate must be read FROM THE CLINICAL
  document, not from the invoice, so the two sources can be compared. If only one
  combined document exists, return the same values you read there. If a value is absent,
  return null.

Perform the following tasks:

1. Document Coverage Check:
   - The claim needs BILLING evidence (an invoice: invoice number, line items, total)
     and CLINICAL evidence (diagnosis and treatment description).
   - Both may come from the same document or from different documents.
   - Set "has_billing_evidence" and "has_clinical_evidence" accordingly.
   - Set "is_valid": false only when one of the two kinds of evidence is missing
     entirely, and say which one in "validation_message".

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
   - When a single combined document is the only source, there is nothing to cross-check:
     set "match_status" to "success" and leave "discrepancies" empty.
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
  "documents": [
    {"file_name": "...", "type": "Invoice", "combined_document": false, "summary": "..."}
  ],
  "has_billing_evidence": true,
  "has_clinical_evidence": true,
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


async def analyze_documents(files):
    """يحلّل أي عدد من الملفات ويستخرج منها مطالبة واحدة.

    لا نفترض أن الملف الأول فاتورة والثاني تقريرًا: الموديل يصنّف كل ملف بنفسه،
    فيقبل ملفًا واحدًا يحمل كل المعلومات، ويرفض ثلاثة ملفات ناقصة.
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        print(f"📄 Processing {len(files)} document(s): {[f['filename'] for f in files]}")

        if not files:
            raise HTTPException(status_code=400, detail="No files were uploaded.")

        seen = {}
        for entry in files:
            if not entry["content"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"The file '{entry['filename']}' is empty.",
                )
            digest = hashlib.sha256(entry["content"]).hexdigest()
            if digest in seen:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{entry['filename']}' and '{seen[digest]}' are the same file. "
                           "Please upload each document only once.",
                )
            seen[digest] = entry["filename"]

        message_content = [{"type": "text", "text": PROMPT}]
        for index, entry in enumerate(files, start=1):
            _append_document_content(
                message_content,
                f"Document {index} of {len(files)} — file name \"{entry['filename']}\":",
                entry["content"], entry["content_type"], entry["filename"],
            )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message_content}],
            response_format={"type": "json_object"},
            temperature=0,
        )

        result_content = json.loads(response.choices[0].message.content)
        print("✅ Enhanced Pipeline Executed Successfully:", result_content)

        return {
            "status": "success",
            "filenames": [entry["filename"] for entry in files],
            **result_content,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ OpenAI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def read_uploads(uploads):
    """يقرأ محتوى الملفات المرفوعة مرة واحدة ويعيد المؤشر لبدايته."""
    entries = []
    for upload in uploads:
        await upload.seek(0)
        entries.append({
            "filename": upload.filename,
            "content_type": upload.content_type,
            "content": await upload.read(),
        })
        await upload.seek(0)
    return entries