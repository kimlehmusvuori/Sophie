"""The follow-up gaps the docket currently tracks.

Each entry is one unanswered thread plus the reply drafted for it. Kept as plain
data so the Streamlit app stays presentation-only and this file can later be
generated from a live mailbox scan instead of hand-maintained.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dossier:
    key: str
    title: str
    counterpart: str
    severity: str  # "urgent" | "high" | "medium"
    age: str
    why: str
    excerpt: str
    excerpt_source: str
    to: list[str]
    subject: str
    draft: str
    cc: list[str] = field(default_factory=list)
    caution: str = ""


DOSSIERS: list[Dossier] = [
    Dossier(
        key="markavtal",
        title="Svenska Markavtal AB — ready to sign, waiting on you",
        counterpart="Fredrik Ericsson (CEO, Svenska Markavtal AB) · cc Erik Vennerlund (Acquify)",
        severity="urgent",
        age="received Thu 13 Aug · still unread · open 4 days",
        why=(
            "Live acquisition. Fredrik said he is ready to move to decision and signing once a "
            "follow-up meeting clears the last questions, and asked you to propose a time "
            '"next week" — that week has now started. Nothing has gone back to him.'
        ),
        excerpt=(
            "Ursäkta sen återkoppling här, vi har fullt upp med några projekt som äter upp min "
            "tid. Kan vi boka ett uppföljningsmöte nästa vecka, när vi är klara med några frågor "
            "så borde vi vara klara för beslut och signering därefter. Välj en tid som passar "
            "ert schema - förutom måndag."
        ),
        excerpt_source="Fredrik Ericsson — Thu 13 Aug",
        to=["fredrik@markavtal.se"],
        cc=["erik@acquify.se"],
        subject="Re: Ametalis indikativa bud",
        draft=(
            "Hej Fredrik,\n\n"
            "Toppen, låter som ni är på god väg!\n\n"
            "Onsdag eftermiddag eller torsdag förmiddag denna vecka funkar bra för oss - säg "
            "vilken tid som passar er bäst så bokar vi in och tar sista frågorna innan "
            "signering.\n\n"
            "// Kim"
        ),
    ),
    Dossier(
        key="boregruppen",
        title="Boregruppen intro — Wednesday pickup not confirmed",
        counterpart="Jens Waldorff (W+) · cc Maximus Ståel von Holstein",
        severity="medium",
        age="received Fri 07:30 · open 4 days",
        why=(
            "Jens offered to collect you at the airport Wednesday ~4pm and drive via B&H to "
            "Boregruppen. You replied in the same thread but only answered the revenue-split "
            "question below it — the logistics were never confirmed."
        ),
        excerpt=(
            "Tonny from Boregruppen in Karlslunde… is ready for a meeting. I suggest Wednesday "
            "after the B&H meeting, maybe around 4 pm. Then I can pick you up at the airport, "
            "drive to B&H, and continue on to Boregruppen. Is that OK?"
        ),
        excerpt_source="Jens Waldorff — Fri 07:30",
        to=["jw@wplus.dk"],
        cc=["maximus.svh@ametalis.com"],
        subject="Re: Quick update: kLAR Miljørådgivning",
        draft=(
            "Hi Jens,\n\n"
            "Wednesday works well — thank you for organising the pickup and the run via B&H to "
            "Boregruppen. See you at the airport around 4pm.\n\n"
            "Best,\n"
            "Kim"
        ),
    ),
    Dossier(
        key="whispr",
        title="Whispr Group intro — who moves first?",
        counterpart="Martin Forslund (Whispr Group)",
        severity="medium",
        age="received Fri 07:24 · open 4 days",
        why=(
            "You connected Martin with Philip for a possible open-data due-diligence "
            "collaboration. He asked a direct one-line question that is still unanswered."
        ),
        excerpt=(
            "Tack också för hänvisningen till Philip. Vi tar dialogen vidare, tar han kontakt "
            "med mig eller ska jag höra av mig till honom? :)"
        ),
        excerpt_source="Martin Forslund — Fri 07:24",
        to=["martin.forslund@whisprgroup.com"],
        cc=[],
        subject="Re: Kompletterande due diligence baserad på öppna datakällor",
        draft=(
            "Hej Martin,\n\n"
            "Gärna hör av dig direkt till Philip - jag flaggar för honom att ni är i kontakt.\n\n"
            "// Kim"
        ),
        caution="Worth a quick Teams message to Philip first, so he is not caught off guard.",
    ),
]
