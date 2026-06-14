# Circulars Folder

Place the real RBI Master Direction PDF here as `kyc_master_direction_2016.pdf`.

Download from rbi.org.in:
- **KYC Master Direction (DBR.AML.BC.No.81/14.01.001/2015-16, updated)** — the primary demo document
- **KYC Amendment 2024** (optional, for drift-detection demo)

For development without the real PDF, the file `sample_kyc_paragraphs.txt`
in this directory contains representative paragraphs the Ingestor can parse.
Point the pipeline at it with:

```bash
python -m src.graph data/circulars/sample_kyc_paragraphs.txt sample_kyc
```

The Ingestor accepts both .pdf and .txt — text files skip PDF extraction
and parse the raw text directly.
