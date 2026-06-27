"""Google Sheets integration for optional manual review layer."""
import gspread
from google.oauth2.service_account import Credentials
from config.settings import get_settings


class SheetsService:
    """Export leads to Google Sheets for manual review/approval."""

    def __init__(self):
        settings = get_settings()
        self.client = None
        self.sheet_id = settings.google_sheet_id
        if settings.google_sheets_credentials:
            try:
                creds = Credentials.from_service_account_file(
                    settings.google_sheets_credentials,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                self.client = gspread.authorize(creds)
            except Exception as e:
                print(f"[Sheets] Failed to initialize: {e}")

    def _get_sheet(self, sheet_name: str = "Leads"):
        if not self.client or not self.sheet_id:
            return None
        try:
            return self.client.open_by_key(self.sheet_id).worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            spreadsheet = self.client.open_by_key(self.sheet_id)
            return spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        except Exception as e:
            print(f"[Sheets] Error accessing sheet: {e}")
            return None

    def export_leads(self, leads: list, sheet_name: str = "Leads"):
        """Export leads to a Google Sheet (clear + rewrite)."""
        sheet = self._get_sheet(sheet_name)
        if not sheet:
            return False

        sheet.clear()
        headers = [
            "ID", "Company", "Website", "Phone", "Email", "Facebook", "LinkedIn",
            "Address", "Google Rating", "Reviews", "Category", "Status", "CRM Status",
            "AI Score", "Created At"
        ]
        sheet.append_row(headers)

        for lead in leads:
            sheet.append_row([
                lead.id, lead.company or "", lead.website or "", lead.phone or "",
                lead.email or "", lead.facebook or "", lead.linkedin or "",
                lead.address or "", lead.google_rating or "", lead.reviews or 0,
                lead.category or "", lead.status.value if lead.status else "",
                lead.crm_status.value if lead.crm_status else "", lead.ai_score or 0,
                lead.created_at.isoformat() if lead.created_at else ""
            ])
        return True

    def export_sequences(self, sequences: list, sheet_name: str = "Sequences"):
        """Export email sequences for manual review."""
        sheet = self._get_sheet(sheet_name)
        if not sheet:
            return False

        sheet.clear()
        headers = ["ID", "Lead Company", "Subject", "Email Body", "Approved", "Created At"]
        sheet.append_row(headers)

        for seq in sequences:
            sheet.append_row([
                seq.id, seq.lead.company if seq.lead else "", seq.subject or "",
                seq.email_body or "", "Yes" if seq.approved else "No",
                seq.created_at.isoformat() if seq.created_at else ""
            ])
        return True
