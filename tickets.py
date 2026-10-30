# -*- coding: utf-8 -*-
"""PDF generation: booking tickets and itineraries, with a QR code that
encodes the booking reference for verification at the gate."""
import io
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

GREEN = colors.HexColor("#0f6b4f")
BLUE = colors.HexColor("#114b7a")
GREY = colors.HexColor("#5c6b73")
LIGHT = colors.HexColor("#eef4f1")
SAND = colors.HexColor("#f6f1e7")


def _qr_image(payload, size=220):
    qr = qrcode.QRCode(box_size=6, border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _header(c, width, height, title, subtitle):
    c.setFillColor(GREEN)
    c.rect(0, height - 34 * mm, width, 34 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(18 * mm, height - 16 * mm, "Karnataka Explore")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor("#cfe6dc"))
    c.drawString(18 * mm, height - 22 * mm, "Discover Karnataka  |  karnatakaexplore.in")
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(width - 18 * mm, height - 16 * mm, title)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#cfe6dc"))
    c.drawRightString(width - 18 * mm, height - 22 * mm, subtitle)


def _footer(c, width, note):
    c.setStrokeColor(colors.HexColor("#d5e2db"))
    c.line(18 * mm, 26 * mm, width - 18 * mm, 26 * mm)
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(GREY)
    c.drawString(18 * mm, 20 * mm, note)
    c.drawString(18 * mm, 16 * mm,
                 "This is a college project. The payment shown on this ticket was simulated - no money was charged.")
    c.setFont("Helvetica", 7.5)
    c.drawRightString(width - 18 * mm, 20 * mm, "Generated " + datetime.now().strftime("%d %b %Y, %I:%M %p"))


def _row(c, x, y, label, value, width, label_w=52 * mm):
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawString(x, y, label)
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor("#14231c"))
    c.drawString(x + label_w, y, str(value) if value not in (None, "") else "-")
    return y - 8.2 * mm


def build_ticket_pdf(booking, user, item_name, item_extra, verify_url):
    """Return PDF bytes for a booking ticket."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    _header(c, width, height, "BOOKING TICKET", booking["booking_ref"])

    y = height - 46 * mm
    c.setFillColor(SAND)
    c.roundRect(18 * mm, y - 20 * mm, width - 36 * mm, 20 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(24 * mm, y - 8 * mm, item_name[:52])
    c.setFont("Helvetica", 9.5)
    c.setFillColor(GREY)
    c.drawString(24 * mm, y - 14 * mm, item_extra or "")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(BLUE)
    c.drawRightString(width - 24 * mm, y - 8 * mm, booking["booking_ref"])

    y -= 30 * mm
    c.setFillColor(colors.HexColor("#14231c"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Traveller details")
    y -= 9 * mm
    y = _row(c, 18 * mm, y, "Name", user["full_name"], width)
    y = _row(c, 18 * mm, y, "Email", user["email"], width)
    y = _row(c, 18 * mm, y, "Mobile", user["mobile"], width)

    y -= 3 * mm
    c.setFillColor(colors.HexColor("#14231c"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Trip details")
    y -= 9 * mm
    y = _row(c, 18 * mm, y, "District", booking.get("district_name") or "-", width)
    if booking["kind"] == "homestay":
        y = _row(c, 18 * mm, y, "Check-in", booking.get("checkin_date"), width)
        y = _row(c, 18 * mm, y, "Check-out", booking.get("checkout_date"), width)
        y = _row(c, 18 * mm, y, "Nights", booking.get("nights"), width)
        y = _row(c, 18 * mm, y, "Rooms", booking.get("rooms"), width)
    elif booking["kind"] == "guide":
        y = _row(c, 18 * mm, y, "Booking date", booking.get("visit_date"), width)
        y = _row(c, 18 * mm, y, "Days", booking.get("nights") or 1, width)
    else:
        y = _row(c, 18 * mm, y, "Visit date", booking.get("visit_date"), width)
    y = _row(c, 18 * mm, y, "Visitors", booking.get("visitors"), width)
    y = _row(c, 18 * mm, y, "Booked on", booking.get("created_at"), width)

    y -= 3 * mm
    c.setFillColor(colors.HexColor("#14231c"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, y, "Payment")
    y -= 9 * mm
    y = _row(c, 18 * mm, y, "Amount", "Rs %s" % format(booking["total"], ",.0f"), width)
    y = _row(c, 18 * mm, y, "Payment status", booking["payment_status"] + " (demo)", width)
    y = _row(c, 18 * mm, y, "Transaction ID", booking.get("txn_id") or "-", width)
    y = _row(c, 18 * mm, y, "Booking status", booking["status"], width)

    # QR block
    qr_buf = _qr_image(verify_url)
    c.drawImage(ImageReader(qr_buf), width - 62 * mm, 34 * mm, 40 * mm, 40 * mm, mask="auto")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GREY)
    c.drawCentredString(width - 42 * mm, 31 * mm, "Scan to verify")

    c.setFillColor(LIGHT)
    c.roundRect(18 * mm, 36 * mm, width - 100 * mm, 34 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(23 * mm, 63 * mm, "Carry this ticket and a photo ID.")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GREY)
    c.drawString(23 * mm, 56 * mm, "Entry timings may change on public holidays and during festivals.")
    c.drawString(23 * mm, 50 * mm, "Cancellations are accepted until 24 hours before the visit date.")
    c.drawString(23 * mm, 44 * mm, "Keep the QR code intact for verification at the gate.")

    _footer(c, width, "Karnataka Explore - smart local tourism portal")
    c.showPage()
    c.save()
    return buf.getvalue()


def build_itinerary_pdf(plan, user):
    """plan = {'days': [[...]], 'total_km': float, 'title': str}"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    _header(c, width, height, "TRAVEL ITINERARY", datetime.now().strftime("%d %b %Y"))

    y = height - 46 * mm
    c.setFillColor(colors.HexColor("#14231c"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(18 * mm, y, plan.get("title") or "My Karnataka itinerary")
    y -= 8 * mm
    c.setFont("Helvetica", 9.5)
    c.setFillColor(GREY)
    c.drawString(18 * mm, y, "Prepared for %s  |  %d day plan  |  approx. %s km" %
                 (user["full_name"], len(plan["days"]), format(plan.get("total_km", 0), ",.0f")))
    y -= 12 * mm

    for i, day in enumerate(plan["days"], 1):
        if y < 60 * mm:
            c.showPage()
            y = height - 30 * mm
        c.setFillColor(GREEN)
        c.roundRect(18 * mm, y - 6 * mm, 26 * mm, 8 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(21 * mm, y - 3.5 * mm, "DAY %d" % i)
        y -= 13 * mm
        for stop in day:
            c.setFont("Helvetica-Bold", 10.5)
            c.setFillColor(colors.HexColor("#14231c"))
            c.drawString(22 * mm, y, stop["name"][:60])
            c.setFont("Helvetica", 8.5)
            c.setFillColor(GREY)
            c.drawString(22 * mm, y - 4.6 * mm,
                         "%s, %s  |  %s" % (stop.get("category", ""), stop.get("district", ""),
                                            stop.get("duration", "")))
            if stop.get("note"):
                c.drawString(22 * mm, y - 9 * mm, stop["note"][:96])
                y -= 4.6 * mm
            y -= 15 * mm
        y -= 4 * mm

    _footer(c, width, "Distances and travel times are estimates - confirm locally before you travel.")
    c.showPage()
    c.save()
    return buf.getvalue()
