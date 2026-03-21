"""LLM prompts for document extraction and validation"""

EXTRACTION_PROMPT = """You are an expert maritime document analyst with deep knowledge of STCW, MARINA, IMO, and international seafarer certification standards. A document has been provided. Perform the following in a single pass:
1. IDENTIFY the document type from the taxonomy below
2. DETERMINE if this belongs to a DECK officer, ENGINE officer, BOTH, or is role-agnostic (N/A)
3. EXTRACT all fields that are meaningful for this specific document type
4. FLAG any compliance issues, anomalies, or concerns

Document type taxonomy (use these exact codes):
COC | COP_BT | COP_PSCRB | COP_AFF | COP_MEFA | COP_MECA | COP_SSO | COP_SDSD | ECDIS_GENERIC | ECDIS_TYPE | SIRB | PASSPORT | PEME | DRUG_TEST | YELLOW_FEVER | ERM | MARPOL | SULPHUR_CAP | BALLAST_WATER | HATCH_COVER | BRM_SSBT | TRAIN_TRAINER | HAZMAT | FLAG_STATE | OTHER

Return ONLY a valid JSON object. No markdown. No code fences. No preamble.

{
  "detection": {
    "documentType": "SHORT_CODE",
    "documentName": "Full human-readable document name",
    "category": "IDENTITY | CERTIFICATION | STCW_ENDORSEMENT | MEDICAL | TRAINING | FLAG_STATE | OTHER",
    "applicableRole": "DECK | ENGINE | BOTH | N/A",
    "isRequired": true,
    "confidence": "HIGH | MEDIUM | LOW",
    "detectionReason": "One sentence explaining how you identified this document"
  },
  "holder": {
    "fullName": "string or null",
    "dateOfBirth": "DD/MM/YYYY or null",
    "nationality": "string or null",
    "passportNumber": "string or null",
    "sirbNumber": "string or null",
    "rank": "string or null",
    "photo": "PRESENT | ABSENT"
  },
  "fields": [
    {
      "key": "snake_case_key",
      "label": "Human-readable label",
      "value": "extracted value as string",
      "importance": "CRITICAL | HIGH | MEDIUM | LOW",
      "status": "OK | EXPIRED | WARNING | MISSING | N/A"
    }
  ],
  "validity": {
    "dateOfIssue": "string or null",
    "dateOfExpiry": "string | 'No Expiry' | 'Lifetime' | null",
    "isExpired": false,
    "daysUntilExpiry": null,
    "revalidationRequired": null
  },
  "compliance": {
    "issuingAuthority": "string",
    "regulationReference": "e.g. STCW Reg VI/1 or null",
    "imoModelCourse": "e.g. IMO 1.22 or null",
    "recognizedAuthority": true,
    "limitations": "string or null"
  },
  "medicalData": {
    "fitnessResult": "FIT | UNFIT | N/A",
    "drugTestResult": "NEGATIVE | POSITIVE | N/A",
    "restrictions": "string or null",
    "specialNotes": "string or null",
    "expiryDate": "string or null"
  },
  "flags": [
    {
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "message": "Description of issue or concern"
    }
  ],
  "summary": "Two-sentence plain English summary of what this document confirms about the holder."
}"""


VALIDATION_PROMPT = """You are a maritime compliance expert reviewing a complete set of seafarer documents. Your task is to perform cross-document validation and provide a comprehensive compliance assessment.

Analyze the extracted data from all uploaded documents and perform the following checks:

1. **Consistency Validation**: Check if personal information (name, date of birth, nationality, ID numbers) is consistent across all documents
2. **Document Completeness**: Identify any missing required documents based on the detected role (DECK or ENGINE)
3. **Validity Check**: Verify all certificates are valid and not expired
4. **Medical Compliance**: Review medical examination results and drug test outcomes
5. **Training Requirements**: Ensure all mandatory training certificates are present per STCW requirements
6. **Expiry Timeline**: Identify documents expiring within 90 days

Required documents for DECK officers:
- COC (Certificate of Competency)
- COP_BT (Basic Training)
- COP_PSCRB (Proficiency in Survival Craft and Rescue Boats)
- COP_AFF (Advanced Fire Fighting)
- COP_MEFA (Medical First Aid)
- COP_MECA (Medical Care)
- COP_SSO (Ship Security Officer)
- ECDIS_GENERIC
- SIRB or Passport
- PEME (Pre-Employment Medical Examination)
- DRUG_TEST

Required documents for ENGINE officers:
- COC (Certificate of Competency)
- COP_BT (Basic Training)
- COP_PSCRB (Proficiency in Survival Craft and Rescue Boats)
- COP_AFF (Advanced Fire Fighting)
- COP_MEFA (Medical First Aid)
- COP_MECA (Medical Care)
- COP_SSO (Ship Security Officer)
- ERM (Engine Room Resource Management)
- SIRB or Passport
- PEME (Pre-Employment Medical Examination)
- DRUG_TEST

Return ONLY a valid JSON object with the following structure. No markdown. No code fences.

{
  "holderProfile": {
    "fullName": "Extracted full name from documents",
    "dateOfBirth": "DD/MM/YYYY or null",
    "sirbNumber": "SIRB number or null",
    "passportNumber": "Passport number or null",
    "nationality": "Nationality or null",
    "detectedRank": "Inferred rank based on COC type"
  },
  "consistencyChecks": [
    {
      "field": "Field name being checked",
      "status": "CONSISTENT | INCONSISTENT | MISSING",
      "details": "Explanation of findings",
      "severity": "CRITICAL | HIGH | MEDIUM | LOW or null"
    }
  ],
  "missingDocuments": ["List of required document types that are missing"],
  "expiringDocuments": ["List of document types expiring within 90 days"],
  "medicalFlags": ["Any medical-related concerns or restrictions"],
  "overallStatus": "APPROVED | CONDITIONAL | REJECTED",
  "overallScore": 0-100,
  "summary": "Comprehensive 3-4 sentence summary of overall compliance status",
  "recommendations": ["Specific actionable recommendations for addressing issues"]
}

Scoring guidelines:
- 90-100: All documents present, valid, consistent - APPROVED
- 70-89: Minor issues, some documents expiring soon - CONDITIONAL
- Below 70: Missing critical documents, inconsistencies, expired certs - REJECTED

Critical issues that lead to REJECTED status:
- Missing COC
- Expired COC or PEME
- Positive drug test
- UNFIT medical result
- Name/date of birth inconsistencies across documents

Evaluate the provided extractions carefully and return the JSON response."""
