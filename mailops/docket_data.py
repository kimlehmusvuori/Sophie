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
        key="syntari_october",
        title="Syntari — Philip wants sign-off before he writes to them",
        counterpart="Philip Hygrell (Ametalis)",
        severity="medium",
        age="received 09:20",
        why=(
            "Following your decision last night, Philip is ready to write to Syntari — but he is "
            "checking the framing first, and he has put a date on it: pausing and coming back "
            "sometime in October. Your own instruction was that this needs a proper review and a "
            "go/no-go decision, so October is a commitment worth making deliberately rather than "
            "by default. Nothing goes out until you answer."
        ),
        excerpt=(
            "Då skriver jag ihop något med att vi lägger det lite på is och återkommer någon gång "
            "i oktober?"
        ),
        excerpt_source="Philip Hygrell — Tue 09:20",
        to=["philip.hygrell@ametalis.com"],
        cc=[],
        subject="Sv: Syntari x Ametalis",
        draft=(
            "Hej Philip,\n\n"
            "Ja, skriv ihop det - men bind oss inte hårt till oktober. Säg att vi återkommer "
            "efter vår interna review, sannolikt under oktober.\n\n"
            "Innan det går ut vill jag att vi stämmer av review'en, så vi vet vad vi faktiskt ska "
            "ha svar på när vi hörs med dem igen. Ta med den punkten till vår sync.\n\n"
            "// Kim"
        ),
        caution=(
            'Softens October to "after our internal review, probably in October". If you are '
            "happy to name the month firmly, drop the qualifier."
        ),
    ),
    Dossier(
        key="ekholm_dates",
        title="Daniel Ekholm — came back with dates, needs you to pick one",
        counterpart="Daniel Ekholm (KPMG)",
        severity="medium",
        age="you replied 18:00 · he answered 18:26 last night",
        why=(
            "You answered his lunch request last night and asked when suited him. He offered today "
            "or Friday this week, or Monday–Tuesday next week, and asked whether one of "
            "those works or whether to aim further out. Ball back with you — and one of "
            "his options is today."
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
        title="Marcus Thomasson — offered you dates, went unanswered for 6 days",
        counterpart="Marcus Thomasson (M.A.C.O Business Development)",
        severity="urgent",
        age="received Wed 12 Aug 20:56 · open 6 days",
        why=(
            "Marcus answered the two wildlife-camera questions in detail and offered concrete "
            "dates: 19 or 20 August, or 1 September in Stockholm from ~15:00. He was explicit "
            "that he has no further travel days in August. On 13 August the mail was forwarded "
            "to Mikael but Marcus himself never got a reply — six days of silence from his side. "
            "The first date he offered, the 19th, is tomorrow — and that is your Denmark "
            "day. There "
            "is also an outstanding promise of the digitalisation draft, and a stated wish "
            "to meet before the 9 September strategy day."
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
        age="Wednesday is tomorrow · your question still unanswered",
        why=(
            "Now confirmed, not just proposed. Bjørn sent the invitation last night at 22:35 and "
            "Jens forwarded it at 22:39: Norion, Wednesday 16:00–16:55, at their premises — that "
            "is tomorrow. Jens had "
            "pencilled Boregruppen (Tonny) for the same Wednesday around 4pm — that slot is gone, "
            "and Jens still has not been told the two collide. Separately, your 14 August "
            "question remains unanswered: you asked for Boregruppen's revenue split because "
            "drilling operations and non-advisory contractor work may make it a poor fit. The "
            "airport pickup was never confirmed either."
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
            "Thanks - Norion Wednesday 16:00-16:55 at their place is in the calendar.\n\n"
            "That means Boregruppen cannot also be at 4pm. Can Tonny take us earlier in the "
            "afternoon, straight after B&H? If not, let us move Boregruppen to another day.\n\n"
            "Before we sit down with Tonny I would still like the revenue split. My hesitation is "
            "the drilling operations and the non-advisory contractor work; if that is a large "
            "share, Boregruppen is probably not the right fit for us and I would rather hold off "
            "than take the meeting.\n\n"
            "And yes to the airport pickup on Wednesday - thank you for organising it.\n\n"
            "Best,\n"
            "Kim"
        ),
        caution=(
            "Norion is now fixed at 16:00–16:55 at their premises, so Boregruppen needs an "
            "earlier slot or another day. Jens is driving you from the airport via B&H."
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
