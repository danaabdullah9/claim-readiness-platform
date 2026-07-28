import os
import json
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

app = FastAPI(title="Claim Readiness Platform - OpenAI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 مفتاح OpenAI الخاص بك
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.post("/analyze-claim")
async def analyze_claim(invoice: UploadFile = File(...), report: UploadFile = File(...)):
    print(f"📄 Processing Claim - Invoice: {invoice.filename}, Report: {report.filename}")
    try:
        # قراءة وتحويل الفاتورة إلى Base64
        invoice_contents = await invoice.read()
        invoice_base64 = f"data:{invoice.content_type or 'image/jpeg'};base64,{base64.b64encode(invoice_contents).decode('utf-8')}"
        
        # قراءة وتحويل التقرير الطبي إلى Base64
        report_contents = await report.read()
        report_base64 = f"data:{report.content_type or 'image/jpeg'};base64,{base64.b64encode(report_contents).decode('utf-8')}"

        prompt = """
        You are an expert medical claims and insurance AI auditor and validator.
        Analyze these TWO images provided very carefully:
        - Image 1: Medical Invoice
        - Image 2: Medical Report

        Perform the following tasks:
        1. Validity Check: 
           - Check if Image 1 is genuinely a medical invoice and Image 2 is genuinely a medical report. 
           - If either is fake, unrelated, or not a medical document, set "is_valid": false and provide a reason in "validation_message". Otherwise, set "is_valid": true.
        
        2. Data Extraction (Priority to Invoice):
           - Extract the 10 required fields: MemberId, NationalId, PatientName, InvoiceNumber, InvoiceDate, HospitalName, DiagnosisCode, DiagnosisDescription, DoctorName, TotalAmount.
           - Give priority to the values found in the Invoice where applicable. If a field is missing, set it to null.

        3. Advanced Clinical & Coverage Analysis (For Human Auditor/Reviewer):
           - "ClinicalSummary": Extract and summarize a detailed clinical note from the medical report (e.g., symptoms, examination findings, procedures performed, and prescribed medications) so the human auditor can make an informed decision without opening the original image.
           - "CoverageHint": Analyze if the treatment appears to be medically necessary (e.g., therapeutic vs cosmetic) based on the report to assist the reviewer.

        4. Cross-Validation & Discrepancy Matching (Smart Matching Rules):
           - Compare common details. Tolerated variations (like minor spelling, triple vs quadruple names, or minor hospital name extensions like "Home") should NOT be flagged as major discrepancies.
           - Critical Discrepancies: Flag fundamental conflicts (e.g., different patient names, different National IDs) in the "discrepancies" array, and set "match_status" to "warning" or "rejected".
        
        Return a strict JSON format with this exact structure:
        {
          "is_valid": true,
          "validation_message": null,
          "match_status": "success", 
          "discrepancies": [],
          "clinical_analysis": {
            "ClinicalSummary": "Detailed summary of symptoms, findings, and treatment from the report...",
            "CoverageHint": "Medical necessity evaluation note..."
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
            "TotalAmount": 0.0
          }
        }
        Return ONLY valid JSON. Do not include any extra text or markdown formatting outside the JSON.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "text", "text": "This is the Medical Invoice:"},
                        {"type": "image_url", "image_url": {"url": invoice_base64}},
                        {"type": "text", "text": "This is the Medical Report:"},
                        {"type": "image_url", "image_url": {"url": report_base64}}
                    ]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)