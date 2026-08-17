import sys
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://localhost:8000"

API_TIMEOUT = 15

UPLOAD_TIMEOUT = 120


# ============================================================
# FIND PDF FILES
# ============================================================

def find_pdfs(folder: Path):

    print(
        "Finding PDF files...",
        flush=True,
    )

    # Only scan the selected folder.
    # We intentionally do NOT use rglob()
    # because the folder is on the Windows /mnt/c drive.

    pdfs = list(
        folder.glob("*.pdf")
    )

    pdfs.sort(
        key=lambda item: item.name.lower()
    )

    return pdfs


# ============================================================
# GET DOCUMENTS FROM API
# ============================================================

def get_documents():

    print(
        "Reading existing documents from API...",
        flush=True,
    )

    response = requests.get(
        f"{API_URL}/documents",
        timeout=API_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "documents",
        [],
    )


# ============================================================
# UPLOAD PDF
# ============================================================

def upload_pdf(pdf_path: Path):

    with pdf_path.open(
        "rb"
    ) as pdf_file:

        response = requests.post(
            f"{API_URL}/documents",
            files={
                "file": (
                    pdf_path.name,
                    pdf_file,
                    "application/pdf",
                )
            },
            timeout=UPLOAD_TIMEOUT,
        )

    response.raise_for_status()

    return response.json()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("RAG PIPELINE - BATCH PDF INGESTION")
    print("=" * 60)
    print()


    # --------------------------------------------------------
    # ARGUMENT
    # --------------------------------------------------------

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            'python batch_ingest.py "/path/to/pdf-folder"'
        )

        print()

        return


    folder = Path(
        sys.argv[1]
    ).expanduser().resolve()


    print(
        f"Folder: {folder}",
        flush=True,
    )

    print(
        f"API: {API_URL}",
        flush=True,
    )

    print()


    # --------------------------------------------------------
    # CHECK FOLDER
    # --------------------------------------------------------

    if not folder.exists():

        print(
            f"ERROR: Folder does not exist:"
        )

        print(
            folder
        )

        return


    if not folder.is_dir():

        print(
            f"ERROR: This is not a folder:"
        )

        print(
            folder
        )

        return


    # --------------------------------------------------------
    # CHECK API
    # --------------------------------------------------------

    print(
        "Checking API...",
        flush=True,
    )


    try:

        response = requests.get(
            f"{API_URL}/health",
            timeout=API_TIMEOUT,
        )

        response.raise_for_status()

        print(
            "API status: OK",
            flush=True,
        )

    except requests.RequestException as exc:

        print(
            "ERROR: API is not reachable.",
            flush=True,
        )

        print(
            f"Details: {exc}",
            flush=True,
        )

        return


    print()


    # --------------------------------------------------------
    # FIND PDFS
    # --------------------------------------------------------

    pdfs = find_pdfs(
        folder
    )


    print(
        f"PDF files found: {len(pdfs)}",
        flush=True,
    )

    print()


    if not pdfs:

        print(
            "No PDF files found."
        )

        return


    # --------------------------------------------------------
    # SHOW PDFS
    # --------------------------------------------------------

    print(
        "Files found:"
    )

    for index, pdf in enumerate(
        pdfs,
        start=1,
    ):

        print(
            f"  {index}. {pdf.name}"
        )


    print()


    # --------------------------------------------------------
    # GET EXISTING DOCUMENTS
    # --------------------------------------------------------

    try:

        documents = get_documents()

    except requests.RequestException as exc:

        print(
            "ERROR: Could not read documents from API."
        )

        print(
            f"Details: {exc}"
        )

        return


    existing_filenames = {
        document.get("filename")
        for document in documents
        if document.get("filename")
    }


    print(
        f"API document records: {len(documents)}",
        flush=True,
    )

    print(
        f"Unique filenames already registered: "
        f"{len(existing_filenames)}",
        flush=True,
    )

    print()


    # --------------------------------------------------------
    # DETERMINE NEW PDFS
    # --------------------------------------------------------

    new_pdfs = []

    skipped_pdfs = []


    for pdf in pdfs:

        if pdf.name in existing_filenames:

            skipped_pdfs.append(
                pdf
            )

        else:

            new_pdfs.append(
                pdf
            )


    print(
        f"New PDFs: {len(new_pdfs)}",
        flush=True,
    )

    print(
        f"Skipped PDFs: {len(skipped_pdfs)}",
        flush=True,
    )

    print()


    # --------------------------------------------------------
    # SKIPPED FILES
    # --------------------------------------------------------

    if skipped_pdfs:

        print(
            "Already registered:"
        )

        for pdf in skipped_pdfs:

            print(
                f"  - {pdf.name}"
            )

        print()


    # --------------------------------------------------------
    # NOTHING NEW
    # --------------------------------------------------------

    if not new_pdfs:

        print(
            "Nothing new to upload.",
            flush=True,
        )

        print(
            "Batch ingestion completed.",
            flush=True,
        )

        return


    # --------------------------------------------------------
    # UPLOAD NEW FILES
    # --------------------------------------------------------

    print(
        "Starting uploads...",
        flush=True,
    )

    print()


    uploaded = 0

    failed = 0


    for index, pdf in enumerate(
        new_pdfs,
        start=1,
    ):

        print(
            f"[{index}/{len(new_pdfs)}] "
            f"{pdf.name}",
            flush=True,
        )


        try:

            result = upload_pdf(
                pdf
            )


            uploaded += 1


            print(
                "    Upload: SUCCESS",
                flush=True,
            )

            print(
                f"    Document ID: "
                f"{result.get('doc_id')}",
                flush=True,
            )

            print(
                f"    Status: "
                f"{result.get('status')}",
                flush=True,
            )


        except requests.RequestException as exc:

            failed += 1


            print(
                "    Upload: FAILED",
                flush=True,
            )

            print(
                f"    Error: {exc}",
                flush=True,
            )


        except Exception as exc:

            failed += 1


            print(
                "    Upload: FAILED",
                flush=True,
            )

            print(
                f"    Error: {exc}",
                flush=True,
            )


        print()


    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("=" * 60)

    print(
        "BATCH INGESTION COMPLETE"
    )

    print("=" * 60)

    print(
        f"PDFs found       : {len(pdfs)}"
    )

    print(
        f"Already registered: {len(skipped_pdfs)}"
    )

    print(
        f"Uploaded         : {uploaded}"
    )

    print(
        f"Failed           : {failed}"
    )

    print()

    print(
        "The uploaded documents are now queued"
    )

    print(
        "for the existing ingestion worker."
    )

    print()


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()
