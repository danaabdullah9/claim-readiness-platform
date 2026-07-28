import os
import json
import base64
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

async def analyze_claim(invoice: UploadFile, report: UploadFile):
    # تعريف العميل هنا يضمن قراءة الـ API Key بشكل صحيح بدون أخطاء
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    try:
        print(f"📄 Processing Claim - Invoice: {invoice.filename}, Report: {report.filename}")
        
        invoice_contents = await invoice.read()
        invoice_base64 = f"data:{invoice.content_type or 'image/jpeg'};base64,{base64.b64encode(invoice_contents).decode('utf-8')}"
        
        report_contents = await report.read()
        report_base64 = f"data:{report.content_type or 'image/jpeg'};base64,{base64.b64encode(report_contents).decode('utf-8')}"

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

        response = client.chat.completions.create(
            model="gpt-4o",
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