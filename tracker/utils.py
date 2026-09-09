from datetime import date
import os
import resend
import base64

def get_current_academic_year():
    today = date.today()
    if today.month >= 5:  # May onwards = new academic year starts
        return f"{today.year}-{str(today.year + 1)[-2:]}"
    else:  # Jan-April = still last year's academic year
        return f"{today.year - 1}-{str(today.year)[-2:]}"




def send_report_email(to_email, file_data, filename, school_name, month, academic_year):
    resend.api_key = os.getenv("RESEND_API_KEY")

    resend.Emails.send({
        "from": "29-Point Programme <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"{school_name} - {month} {academic_year} Report",
        "html": f"""
            <p>Dear Officer,</p>
            <p>
                The 29-Point Programme report for
                <strong>{month} {academic_year}</strong>
                has been submitted by
                <strong>{school_name}</strong>.
            </p>
            <p>Please find the complete report attached.</p>
            <p>Regards,<br>29-Point Programme Tracker</p>
        """,
        "attachments": [
            {
                "filename": filename,
                "content": list(file_data),
            }
        ],
    })

