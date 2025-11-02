from fastapi import APIRouter, HTTPException

from services.report.generator import ReportGenerator


router = APIRouter()


@router.post("/report/download")
async def download_report(page_id: str):
    """
    Endpoint to download a report based on the provided page_id.
    This will send the pre-loaded content to the API for optimized report generation.
    """
    try:
        if not page_id:
            raise HTTPException(status_code=400, detail="page_id parameter is required")

        generator = ReportGenerator()
        report_content = await generator.get_report_content(page_id)

        if not report_content:
            raise HTTPException(status_code=404, detail="Report content not found")

        return {
            "status": "success",
            "report_content": report_content,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
