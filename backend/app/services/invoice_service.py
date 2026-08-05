import io
import datetime
from typing import Dict, Any, List

class InvoiceGenerator:
    """
    Enterprise PDF & HTML Invoice Generation Engine.
    Generates downloadable invoices with breakdown, tax calculations, and payment status.
    """

    @staticmethod
    def generate_invoice_html(
        invoice_number: str,
        org_name: str,
        amount_due: float,
        amount_paid: float,
        tax_amount: float,
        currency: str,
        status: str,
        created_at: str,
        items: List[Dict[str, Any]]
    ) -> str:
        subtotal = sum(item.get("amount", 0.0) for item in items)
        total = subtotal + tax_amount

        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #E2E8F0; color: #1E293B;">{item.get('description', 'Subscription Service')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #E2E8F0; text-align: center; color: #1E293B;">{item.get('quantity', 1)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #E2E8F0; text-align: right; color: #1E293B;">${item.get('unit_amount', 0.0):,.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #E2E8F0; text-align: right; color: #1E293B; font-weight: 600;">${item.get('amount', 0.0):,.2f}</td>
            </tr>
            """

        status_color = "#10B981" if status == "paid" else "#F59E0B"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Invoice {invoice_number} - MetaMind AI</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0F172A; margin: 0; padding: 40px; background-color: #F8FAFC; }}
        .invoice-card {{ max-width: 800px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; border-bottom: 2px solid #F1F5F9; padding-bottom: 24px; }}
        .brand {{ font-size: 24px; font-weight: 800; color: #2563EB; letter-spacing: -0.5px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; background-color: {status_color}15; color: {status_color}; border: 1px solid {status_color}30; }}
        .details-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
        .label {{ font-size: 12px; text-transform: uppercase; color: #64748B; font-weight: 600; margin-bottom: 4px; }}
        .value {{ font-size: 15px; font-weight: 600; color: #1E293B; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 32px; }}
        th {{ background: #F8FAFC; text-align: left; padding: 12px; font-size: 12px; text-transform: uppercase; color: #64748B; border-bottom: 2px solid #E2E8F0; }}
        .totals {{ max-width: 300px; margin-left: auto; border-top: 2px solid #E2E8F0; padding-top: 16px; }}
        .totals-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; color: #475569; }}
        .totals-grand {{ font-size: 18px; font-weight: 800; color: #0F172A; border-top: 1px solid #E2E8F0; padding-top: 8px; margin-top: 8px; }}
        .footer {{ margin-top: 40px; text-align: center; font-size: 13px; color: #94A3B8; border-top: 1px solid #F1F5F9; padding-top: 24px; }}
    </style>
</head>
<body>
    <div class="invoice-card">
        <div class="header">
            <div>
                <div class="brand">MetaMind AI</div>
                <div style="font-size: 13px; color: #64748B; margin-top: 4px;">Enterprise SaaS Advertising Engine</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 20px; font-weight: 700; color: #1E293B;">INVOICE</div>
                <div style="font-size: 14px; color: #64748B; font-family: monospace;">#{invoice_number}</div>
                <div style="margin-top: 8px;"><span class="badge">{status}</span></div>
            </div>
        </div>

        <div class="details-grid">
            <div>
                <div class="label">Billed To</div>
                <div class="value">{org_name}</div>
                <div style="font-size: 13px; color: #64748B; margin-top: 2px;">Organization ID: {org_name.lower().replace(' ', '-')}</div>
            </div>
            <div style="text-align: right;">
                <div class="label">Date Issued</div>
                <div class="value">{created_at[:10] if created_at else '2026-07-25'}</div>
                <div class="label" style="margin-top: 12px;">Currency</div>
                <div class="value">{currency}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Unit Price</th>
                    <th style="text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span>Subtotal:</span>
                <span>${subtotal:,.2f}</span>
            </div>
            <div class="totals-row">
                <span>Tax (0%):</span>
                <span>${tax_amount:,.2f}</span>
            </div>
            <div class="totals-row totals-grand">
                <span>Total Paid:</span>
                <span>${amount_paid:,.2f}</span>
            </div>
        </div>

        <div class="footer">
            Thank you for choosing MetaMind AI. For billing inquiries, contact billing@metamind.ai
        </div>
    </div>
</body>
</html>
"""
        return html_content

invoice_generator = InvoiceGenerator()
