"""Curated AI-disclosure / AI-transparency mandate dataset.

Sources are the governing authority pages (real references). Scope modeling
choices are documented inline. This is a knowledge base, not legal advice --
the applicability engine treats each entry as a structured rule.

Status legend:
  in_force  -> currently enforceable; gaps count toward the risk score
  upcoming  -> passed but not yet in effect on the reference date (watched)
  proposed  -> not yet enacted (watched, never scored)
"""
from __future__ import annotations

from datetime import date

from .models import Mandate, MandateStatus, Obligation, Severity

_OB = Obligation  # shorthand


MANDATES: tuple = (
    Mandate(
        mid="nyc-ll144",
        jurisdiction="US-NY",
        title="NYC Local Law 144 (Automated Employment Decision Tools)",
        summary="Employers using automated tools for hiring/ promotion must run "
        "an independent bias audit, disclose to candidates, and publish results.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2023, 7, 5),
        scope_sectors=("employment",),
        scope_uses=("hiring",),
        penalty="Civil penalties up to $500 (first) / $1,500 (subsequent) per "
        "violation per day.",
        source="https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page",
        obligations=(
            _OB("bias_audit", "Independent bias audit within past year",
                "Engage an independent auditor; publish the bias audit.",
                Severity.CRITICAL),
            _OB("candidate_disclosure", "Candidate & job-ad disclosure",
                "Notify candidates and post a disclosure in each job listing.",
                Severity.HIGH),
            _OB("summary_results", "Publish summary results",
                "Make the bias-audit summary results publicly available.",
                Severity.HIGH),
            _OB("record_keeping", "Retain records 3 years",
                "Keep audit + notices for at least 3 years.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="co-aia",
        jurisdiction="US-CO",
        title="Colorado AI Act (High-Risk AI Systems)",
        summary="Requires risk-management programs and impact assessments for "
        "high-risk AI systems, plus consumer disclosure of AI interaction.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2026, 6, 30),
        scope_sectors=None,  # high-risk AI across all sectors
        scope_uses=("hiring", "biometric", "facial_recognition",
                    "content_generation", "recommendation",
                    "customer_support", "surveillance"),
        penalty="Enforced by the Colorado Attorney General.",
        source="https://coag.gov/resources/colorado-ai-act/",
        obligations=(
            _OB("impact_assessment", "Completed impact assessment",
                "Risk assessment of reasonably foreseeable harms before "
                "deployment and on a periodic basis.",
                Severity.CRITICAL),
            _OB("risk_management", "Risk-management program",
                "Documented risk-management policy and program.",
                Severity.HIGH),
            _OB("disclosure", "Consumer disclosure of AI use",
                "Tell consumers they are interacting with AI and how to "
                "opt out where feasible.",
                Severity.HIGH),
            _OB("reporting", "Report known violations to AG",
                "Report known or reasonably foreseeable high-risk-system "
                "violations to the Attorney General.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="eu-aiact-13",
        jurisdiction="EU",
        title="EU AI Act -- Art. 13 Transparency",
        summary="Transparency obligations for AI that interacts with humans, "
        "generates/deepfakes content, or performs emotion/biometric categorisation.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2025, 2, 2),
        scope_sectors=None,
        scope_uses=("content_generation", "facial_recognition", "biometric",
                    "emotion_recognition", "surveillance"),
        penalty="Up to EUR 15M or 3% of worldwide annual turnover.",
        source="https://artificialintelligenceact.eu/article/13/",
        obligations=(
            _OB("transparency_disclosure", "Inform users they interact with AI",
                "Natural persons must be informed they interact with AI or "
                "that content is AI-generated.",
                Severity.HIGH),
            _OB("watermark", "Machine-readable watermark on synthetic content",
                "Mark deepfake / AI-generated content with watermarks and "
                "disclose its artificial origin.",
                Severity.HIGH),
            _OB("human_oversight", "Ensure human oversight",
                "Implement measures for effective human oversight.",
                Severity.HIGH),
            _OB("technical_docs", "Technical documentation available",
                "Maintain and make technical documentation available.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="eu-aiact-gpai",
        jurisdiction="EU",
        title="EU AI Act -- Art. 53 GPAI Provider Obligations",
        summary="Obligations for general-purpose AI model providers (documentation, "
        "risk monitoring, copyright compliance, training-data summary).",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2025, 8, 2),
        scope_sectors=None,
        scope_uses=("content_generation",),
        penalty="Up to EUR 35M or 7% of worldwide annual turnover.",
        source="https://artificialintelligenceact.eu/article/53/",
        obligations=(
            _OB("provider_obligations", "Provider documentation & monitoring",
                "Technical documentation, risk monitoring, EU representative.",
                Severity.HIGH),
            _OB("copyright_policy", "EU copyright & training-data summary",
                "Put EU-copyright policy in place and publish a training-data "
                "summary.",
                Severity.HIGH),
        ),
    ),
    Mandate(
        mid="ca-ab3030",
        jurisdiction="US-CA",
        title="California AB 3030 (Health/Coverage Contract GenAI Disclosures)",
        summary="Providers of generative AI that produce patient/contract content "
        "must label it as AI-generated and provide a detection method.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2025, 1, 1),
        scope_sectors=None,
        scope_uses=("content_generation",),
        penalty="Enforced by the California Privacy Protection Agency / AG.",
        source="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202320240AB3030",
        obligations=(
            _OB("content_label", "Disclose content is AI-generated",
                "Clearly state the content was generated by AI.",
                Severity.HIGH),
            _OB("provenance", "Prohibit deceptive synthetic content",
                "No deceptive or destructive synthetic content; provide "
                "provenance.",
                Severity.MEDIUM),
            _OB("detection_method", "Offer detection method",
                "Provide a way to detect the synthetic content.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="ca-ab453",
        jurisdiction="US-CA",
        title="California AB 453 (Bot Disclosure)",
        summary="A bot used to communicate with a person online must disclose it "
        "is not a human.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2024, 7, 1),
        scope_sectors=None,
        scope_uses=("customer_support",),
        penalty="Enforced by the California Attorney General.",
        source="https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202320240AB453",
        obligations=(
            _OB("bot_disclosure", "Disclose the bot is not human",
                "Clear & conspicuous disclosure that the bot is not a human.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="il-bipa",
        jurisdiction="US-IL",
        title="Illinois Biometric Information Privacy Act (BIPA)",
        summary="Governs collection of biometric identifiers (incl. facial "
        "recognition) -- requires written consent and a retention policy.",
        status=MandateStatus.IN_FORCE,
        effective_date=date(2008, 10, 1),
        scope_sectors=None,
        scope_uses=("biometric", "facial_recognition"),
        penalty="Private right of action; $1k (negligent)/$5k (intentional) "
        "per violation.",
        source="https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3004",
        obligations=(
            _OB("written_consent", "Informed written consent",
                "Obtain written consent before collecting biometric data.",
                Severity.CRITICAL),
            _OB("retention_policy", "Public retention/destruction schedule",
                "Publish a retention schedule and destroy data when purpose met.",
                Severity.HIGH),
            _OB("no_sale", "No sale of biometrics",
                "Prohibit sale of biometric identifiers.",
                Severity.HIGH),
        ),
    ),
    # ---- PROPOSED / MONITOR ONLY (never scored) ----
    Mandate(
        mid="nyc-listing-ai",
        jurisdiction="US-NY",
        title="NYC Proposed AI Listing-Image Disclosure (real estate)",
        summary="Proposal: landlords/realtors must disclose and label AI-generated "
        "listing images and AI use in property listings.",
        status=MandateStatus.PROPOSED,
        effective_date=None,
        scope_sectors=("real_estate",),
        scope_uses=("listing_generation", "content_generation"),
        penalty="Proposed -- not yet enforced.",
        source="https://www.nyc.gov/",
        obligations=(
            _OB("listing_disclosure", "Disclose AI-generated listing content",
                "Disclose when listings use AI-generated images/content.",
                Severity.HIGH),
            _OB("label_ai", "Label AI-used listings",
                "Visibly label listings that used AI.",
                Severity.MEDIUM),
        ),
    ),
    Mandate(
        mid="au-vic-demask",
        jurisdiction="AU-VIC",
        title="Victoria (AU) Proposed Social-Media Demasking Powers",
        summary="Proposal: powers to identify anonymous accounts behind harmful "
        "AI-driven surveillance/abuse on social platforms.",
        status=MandateStatus.PROPOSED,
        effective_date=None,
        scope_sectors=None,
        scope_uses=("surveillance",),
        penalty="Proposed -- not yet enacted.",
        source="https://www.theguardian.com/australia-news/2026/jul/19/victoria-proposes-social-media-account-identification-powers",
        obligations=(
            _OB("identity_disclosure", "Identify anonymous accounts",
                "Provide means to identify accounts behind harmful AI use.",
                Severity.MEDIUM),
        ),
    ),
)


def load_mandates() -> tuple:
    """Return the curated mandate dataset (immutable tuple)."""
    return MANDATES
