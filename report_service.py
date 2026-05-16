"""PDF car reports and email delivery."""

from __future__ import annotations

import io
import logging
import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

REPORT_KEYWORDS = [
    "report", "rapport", "pdf", "send me", "email me", "e-mail",
    "mail me", "envoyer", "envoie", "envoyez", "par email", "par e-mail",
    "i want a report", "generate a report", "car report", "vehicle report",
]

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")


def extract_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text.strip())
    return match.group(0).lower() if match else None


def is_report_request(question: str, normalize_fn: Callable[[str], str]) -> bool:
    q = normalize_fn(question)
    return any(k in q for k in REPORT_KEYWORDS)


def _safe_get(d: Optional[dict], key: str, default="N/A"):
    if not isinstance(d, dict):
        return default
    val = d.get(key, default)
    return default if val is None else val


def car_label(doc: dict) -> str:
    marque = str(doc.get("marque", "Unknown"))
    modele = str(doc.get("modele", "Unknown"))
    annee = doc.get("annee", "")
    if annee:
        return f"{marque} {modele} ({annee})"
    return f"{marque} {modele}"


def parse_car_from_chunk(chunk: str) -> tuple[str, str]:
    marque = modele = ""
    for line in chunk.split("\n"):
        line = line.strip()
        if line.startswith("marque:"):
            marque = line.split(":", 1)[1].strip()
        elif line.startswith("modele:"):
            modele = line.split(":", 1)[1].strip()
    return marque, modele


def find_car_in_records(
    question: str,
    car_records: list[dict],
    normalize_fn: Callable[[str], str],
    retrieve_fn: Optional[Callable[[str, int], list[dict]]] = None,
) -> Optional[dict]:
    if not car_records:
        return None

    q = normalize_fn(question)
    matches = []
    for doc in car_records:
        marque = normalize_fn(str(doc.get("marque", "")))
        modele = normalize_fn(str(doc.get("modele", "")))
        if marque and marque in q:
            matches.append(doc)
        elif modele and modele in q and (not marque or marque in q):
            matches.append(doc)

    if len(matches) == 1:
        return matches[0]
    if matches:
        return matches[0]

    if retrieve_fn:
        results = retrieve_fn(question, top_k=3)
        for hit in results:
            marque, modele = parse_car_from_chunk(hit.get("chunk", ""))
            if not marque and not modele:
                continue
            for doc in car_records:
                if (
                    normalize_fn(str(doc.get("marque", ""))) == normalize_fn(marque)
                    and normalize_fn(str(doc.get("modele", ""))) == normalize_fn(modele)
                ):
                    return doc

    return None


def build_pdf_report(doc: dict) -> bytes:
    buffer = io.BytesIO()
    doc_pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Car Report — {car_label(doc)}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#c0392b"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )

    motor = doc.get("motorisation", {}) or {}
    price = doc.get("prix", {}) or {}
    dims = doc.get("dimensions", {}) or {}
    warranty = doc.get("garantie", {}) or {}
    constructeur = doc.get("constructeur", {}) or {}

    reviews = doc.get("avis", []) or []
    review_count = len(reviews)
    avg_rating = (
        round(sum(float(r.get("note", 0)) for r in reviews) / review_count, 2)
        if review_count
        else "N/A"
    )

    colors_list = doc.get("couleurs_disponibles", []) or []
    equipment = doc.get("equipements", []) or []

    story = [
        Paragraph("NIDIX AI — Vehicle Report", title_style),
        Paragraph(car_label(doc), styles["Heading2"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"<b>Type:</b> {_safe_get(doc, 'type_vehicule')} · "
            f"<b>Body:</b> {_safe_get(doc, 'carrosserie')} · "
            f"<b>Segment:</b> {_safe_get(doc, 'segment')}",
            body_style,
        ),
        Paragraph(
            f"<b>Manufacturer country:</b> {_safe_get(constructeur, 'pays')}",
            body_style,
        ),
    ]

    def section(title: str, rows: list[tuple[str, str]]):
        story.append(Paragraph(title, heading_style))
        data = [["Specification", "Value"]] + [[k, str(v)] for k, v in rows]
        table = Table(data, colWidths=[7 * cm, 9 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2 * cm))

    section("Motorisation", [
        ("Fuel type", _safe_get(motor, "type_carburant")),
        ("Transmission", _safe_get(motor, "transmission")),
        ("Power (ch)", _safe_get(motor, "puissance_ch")),
        ("Torque (Nm)", _safe_get(motor, "couple_nm")),
        ("Consumption (L/100km)", _safe_get(motor, "consommation_l100km")),
        ("Consumption (kWh/100km)", _safe_get(motor, "consommation_kwh100km")),
        ("CO2 (g/km)", _safe_get(motor, "emissions_co2_gkm")),
        ("Range (km)", _safe_get(motor, "autonomie_km")),
        ("Battery (kWh)", _safe_get(motor, "batterie_kwh")),
    ])

    section("Pricing (EUR)", [
        ("Total TTC", _safe_get(price, "prix_total_ttc_eur")),
        ("Base price", _safe_get(price, "prix_base_eur")),
        ("Monthly lease", _safe_get(price, "loyer_mensuel_eur")),
    ])

    section("Dimensions", [
        ("Trunk (L)", _safe_get(dims, "coffre_litres")),
        ("Seats", _safe_get(dims, "nombre_places")),
        ("Doors", _safe_get(dims, "nombre_portes")),
    ])

    section("Warranty & reviews", [
        ("Warranty (years)", _safe_get(warranty, "duree_ans")),
        ("Review count", review_count),
        ("Average rating", avg_rating),
    ])

    if colors_list:
        story.append(Paragraph("Available colors", heading_style))
        story.append(Paragraph(", ".join(colors_list[:12]), body_style))

    if equipment:
        story.append(Paragraph("Key equipment", heading_style))
        eq_text = "<br/>".join(f"• {e}" for e in equipment[:15])
        story.append(Paragraph(eq_text, body_style))

    if reviews:
        story.append(Paragraph("Sample reviews", heading_style))
        for rev in reviews[:3]:
            note = rev.get("note", "N/A")
            comment = str(rev.get("commentaire", ""))[:200]
            story.append(Paragraph(f"<b>{note}/5</b> — {comment}", body_style))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<i>Generated by NIDIX AI from your indexed vehicle database.</i>",
        body_style,
    ))

    doc_pdf.build(story)
    buffer.seek(0)
    return buffer.read()


def send_report_email(to_email: str, car_doc: dict, pdf_bytes: bytes) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError(
            "Email is not configured. Set SMTP_USER and SMTP_PASSWORD environment variables."
        )

    label = car_label(car_doc)
    safe_name = re.sub(r"[^\w\-]+", "_", label)[:60]
    filename = f"nidix_report_{safe_name}.pdf"

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = f"Your NIDIX AI vehicle report — {label}"

    body = f"""Hello,

Please find attached your PDF vehicle report for {label}.

This report was generated by NIDIX AI.

Best regards,
NIDIX AI
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=filename,
    )
    msg.attach(attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(msg["From"], [to_email], msg.as_string())

    logger.info("Report email sent to %s for %s", to_email, label)
