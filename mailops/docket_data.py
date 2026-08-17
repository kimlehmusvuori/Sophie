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
        key="ekholm_dates",
        title="Daniel Ekholm — came back with dates, needs you to pick one",
        counterpart="Daniel Ekholm (KPMG)",
        severity="medium",
        age="you replied 18:00 · he answered 18:26",
        why=(
            "You answered his lunch request at 18:00 and asked when suited him. He offered "
            "tomorrow or Friday this week, or Monday–Tuesday next week, and asked whether one of "
            "those works or whether to aim further out. Ball back with you."
        ),
        excerpt=(
            "Imorgon lr fredag den här veckan, och mån-tis nästa vecka funkar bra för mig. Någon "
            "av dessa dagar som funkar för dig lr skall vi försöka hitta en tid lite längre fram?"
        ),
        excerpt_source="Daniel Ekholm — Mon 18:26",
        to=["daniel.ekholm@kpmg.se"],
        cc=[],
        subject="Re: Lunch",
        draft=(
            "Hej Daniel,\n\n"
            "Fredag funkar bäst för mig den här veckan - säg 12:00? Passar inte det landar vi på "
            "måndag eller tisdag nästa vecka istället.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Check Friday against the AI review lunch — that moved out of Friday when you "
            "redirected Philip, but the new slot is not booked yet."
        ),
    ),
    Dossier(
        key="marcus",
        title="Marcus Thomasson — offered you dates, went unanswered for 5 days",
        counterpart="Marcus Thomasson (M.A.C.O Business Development)",
        severity="urgent",
        age="received Wed 12 Aug 20:56 · open 5 days",
        why=(
            "Marcus answered the two wildlife-camera questions in detail and offered concrete "
            "dates: 19 or 20 August, or 1 September in Stockholm from ~15:00. He was explicit "
            "that he has no further travel days in August. On 13 August the mail was forwarded "
            "to Mikael but Marcus himself never got a reply — five days of silence from his "
            "side, and the August window closes this week. There is also an outstanding promise "
            "of the digitalisation draft, and a stated wish to meet before the 9 September "
            "strategy day."
        ),
        excerpt=(
            "Den 1 september är jag i Stockholm för ett styrelsemöte med Freedom och kan träffas "
            "från cirka kl. 15.00 och framåt. Om du gärna vill få till ett möte redan i augusti "
            "skulle jag även kunna komma upp den 19 eller 20 augusti… Tyvärr har jag inte "
            "möjlighet till fler resdagar under augusti."
        ),
        excerpt_source="Marcus Thomasson — Wed 12 Aug 20:56",
        to=["marcus.thomasson@macoab.se"],
        cc=[],
        subject="Sv: Kort update / tack för bra samtal!",
        draft=(
            "Hej Marcus,\n\n"
            "Tack för ett grundligt svar - och ursäkta att jag varit tyst, det har varit fullt "
            "sedan AI-outingen.\n\n"
            "Onsdag den 19:e är jag i Danmark, så den funkar inte. Torsdag den 20:e i Stockholm "
            "skulle däremot passa mig bra - säg till om det fungerar för dig, annars bokar vi "
            "1 september från 15:00.\n\n"
            "Din genomgång av viltkamera-lösningen var intressant. Jag delade den med Mikael, "
            "och hans bild är att AI-delen redan fungerar bra för art och antal - individnivå är "
            "det som skulle vara nytt. Vi tar det vidare när vi ses.\n\n"
            "Inför strategidagen den 9 september skickar jag ut materialet senast en vecka "
            "innan, så det vore värdefullt att ha hunnit prata före dess.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Assumes Wednesday the 19th is your Denmark day (per the Boregruppen thread) — check "
            "the calendar first. You also still owe him the digitalisation draft."
        ),
    ),
    Dossier(
        key="boregruppen",
        title="Boregruppen — now collides with Norion on Wednesday",
        counterpart="Jens Waldorff (W+) · cc Maximus Ståel von Holstein",
        severity="urgent",
        age="proposed Fri 14 Aug · your question still unanswered",
        why=(
            "Jens proposed Boregruppen (Tonny) for Wednesday around 4pm. Tonight you agreed to "
            "put Norion at 4–5pm the same Wednesday. Those two cannot both stand, and Jens has "
            "not been told. Separately, your 14 August question is still unanswered: you asked "
            "for Boregruppen's revenue split because drilling operations and non-advisory "
            "contractor work may make it a poor fit. The airport pickup was never confirmed "
            "either."
        ),
        excerpt=(
            "I suggest Wednesday after the B&H meeting, maybe around 4 pm. Then I can pick you up "
            "at the airport, drive to B&H, and continue on to Boregruppen. Is that OK?"
        ),
        excerpt_source="Jens Waldorff — Fri 14 Aug 09:30",
        to=["jw@wplus.dk"],
        cc=["maximus.svh@ametalis.com"],
        subject="Re: Quick update: kLAR Miljørådgivning",
        draft=(
            "Hi Jens,\n\n"
            "One more thing on Wednesday: you had suggested Boregruppen around 4pm, and we have "
            "now put Norion at 4-5pm. Those clash - can we fit both with Boregruppen earlier, or "
            "should we move one?\n\n"
            "Before we sit down with Tonny I would still like the revenue split. My hesitation is "
            "the drilling operations and the non-advisory contractor work; if that is a large "
            "share, Boregruppen is probably not the right fit for us and I would rather hold off "
            "than take the meeting.\n\n"
            "And yes to the airport pickup on Wednesday - thank you for organising it.\n\n"
            "Best,\n"
            "Kim"
        ),
        caution=(
            "Replaces the earlier draft, which would have confirmed a 4pm Boregruppen meeting "
            "that now conflicts with Norion."
        ),
    ),
    Dossier(
        key="adilson_christer",
        title="Christer meeting — Adilson proposed a window, needs your yes",
        counterpart="Adilson Fonseca (MVI) · Thy",
        severity="medium",
        age="received 19:59",
        why=(
            "This answers the timing question carried on the Thy thread since Friday. Adilson "
            "expects the agreements done mid-week and proposes early next week for Christer, with "
            "room to sync with PEJ first. He put it as a question, so it stays open until you "
            "confirm."
        ),
        excerpt=(
            "Förväntar mig att vi borde vara klara med avtalen i mitten på denna vecka, så kanske "
            "i början på nästa lär vara lämplig tidpunkt? Kan vara bra att ha lite luft så du "
            "hinner stämma av med PEJ innan du sätter dig med christer."
        ),
        excerpt_source="Adilson Fonseca — Mon 19:59",
        to=["adilson.fonseca@mvi.se"],
        cc=[],
        subject="RE: Thy - New employment agreements",
        draft=(
            "Hej Adilson,\n\n"
            "Låter bra - vi siktar på början av nästa vecka för Christer, så hinner jag stämma av "
            "med PEJ först.\n\n"
            "Säg till när avtalen är klara, så bokar jag in det.\n\n"
            "Mvh, Kim"
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
