"""Reporting and exports routes."""

import io
import csv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.database import get_db
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.user import User
from app.models.blood_request import BloodRequest
from app.models.hospital import Hospital
from app.auth.auth_dependencies import get_current_admin

router = APIRouter(
    prefix="/admin/reports",
    tags=["Reports"]
)


@router.get("/donations/csv")
def export_donations_csv(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Export donation history log to CSV (Excel compatible).
    """
    donations = db.query(Donation).all()

    # Generate CSV stream
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Donation ID", "Donor Name", "Blood Group", "Request ID",
        "Hospital ID", "Status", "Certificate Code", "Donation Date"
    ])

    for d in donations:
        # Resolve names
        donor = db.query(Donor).filter(Donor.id == d.donor_id).first()
        donor_name = "Unknown"
        blood_grp = "N/A"
        if donor:
            donor_user = db.query(User).filter(User.id == donor.user_id).first()
            if donor_user:
                donor_name = donor_user.full_name
            blood_grp = donor.blood_group

        req = db.query(BloodRequest).filter(BloodRequest.id == d.request_id).first()
        hosp_id = req.hospital_id if req else "N/A"

        writer.writerow([
            d.id, donor_name, blood_grp, d.request_id, hosp_id,
            d.status, d.certificate_code or "N/A", d.donated_at
        ])

    output.seek(0)
    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=donations_report_{datetime.now().strftime('%Y%m%d')}.csv"
    return response


@router.get("/donations/summary")
def get_donations_summary_report(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Fetch a text/JSON summary of monthly metrics, hospital counts, and success factors.
    """
    donations = db.query(Donation).all()

    total_count = len(donations)
    completed_count = sum(1 for d in donations if d.status == "completed")
    pending_count = sum(1 for d in donations if d.status == "pending")

    # Generate an ASCII text report layout
    report_lines = [
        "==================================================",
        "          SMART BLOOD FINDER SYSTEM REPORT         ",
        "==================================================",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Recorded Donations: {total_count}",
        f"Verified & Completed   : {completed_count}",
        f"Pending Verification    : {pending_count}",
        "--------------------------------------------------",
        "Recent Donation Log Summary:",
        "--------------------------------------------------"
    ]

    for d in donations[:20]:  # Limit to 20 for preview
        donor = db.query(Donor).filter(Donor.id == d.donor_id).first()
        donor_name = "Unknown"
        if donor:
            donor_user = db.query(User).filter(User.id == donor.user_id).first()
            if donor_user:
                donor_name = donor_user.full_name
        report_lines.append(
            f"ID: {d.id} | Donor: {donor_name} | Status: {d.status} | Date: {d.donated_at.strftime('%Y-%m-%d') if d.donated_at else 'N/A'}"
        )

    report_lines.append("==================================================")
    report_text = "\n".join(report_lines)

    response = StreamingResponse(
        iter([report_text]),
        media_type="text/plain"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=donations_summary_{datetime.now().strftime('%Y%m%d')}.txt"
    return response
