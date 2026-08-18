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
        key="filipovic_pfas",
        title="PFAS reference — Relement is bidding the same tender",
        counterpart="Marko Filipovic (Sellén Filipovic) · via Linus Nilsson, Relement",
        severity="urgent",
        age="only you can close this — Emma left it open at 14:06",
        why=(
            "You told Marko at 11:12 that you thought the group had the references and would come "
            "back asap, then forwarded the request to Relement and Envima. Six minutes later Linus "
            "answered: Relement is bidding on the same MCF procurement themselves, with all the "
            "competencies and references in-house. Supplying a reference would be arming a rival "
            "bid against your own portfolio company. At 14:06 Emma answered Marko directly and "
            "cleared the rest of the group — Envima is SME-scale, Etha, Westberg and Natur og "
            "Samfunn have no PFAS — but she also told him Relement would come back to him soon. "
            "She does not know they are bidding. So the only open promise in the thread is one "
            "you cannot keep, and you are the only person who knows that."
        ),
        excerpt=(
            "Vi fick dock just in ett systerföretag i gruppen som heter Relement. Kim har kollat "
            "med dem, så de återkommer snart."
        ),
        excerpt_source="Emma Karlsson to Marko, you on Cc — Tue 14:06",
        to=["marko@sellenfilipovic.se"],
        cc=["emma.karlsson@envima.se", "anna.lindberg@envima.se"],
        subject="Re: Referens till en större upphandling",
        draft=(
            "Hej Marko,\n\n"
            "Emma har redan svarat dig om Envima och de andra bolagen, så jag fyller i den sista "
            "biten.\n\n"
            "Relement lämnar anbud på samma upphandling själva och har kompetenserna och "
            "referenserna in-house. Då kan jag inte gå in och stötta ett konkurrerande anbud med "
            "referenser - det vore inte rätt mot dem. Så du behöver inte vänta på mer från vår "
            "sida i den här.\n\n"
            "Ursäkta att jag gav dig en annan bild i morse, innan jag hade kollat. Hör gärna av "
            "dig i andra sammanhang, det finns mycket annat vi kan prata om.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Emma and Anna are on Cc so Emma sees the promise closed — she is expecting Relement "
            "to answer Marko and would otherwise chase them. Separately: her mail told an outside "
            "party that Relement was just acquired into the group. Worth a word with her, but not "
            "in this reply."
        ),
    ),
    Dossier(
        key="needo",
        title="Jonathan Wintzell (Needo) — tried to call, wants lunch",
        counterpart="Jonathan Wintzell (CEO, Needo)",
        severity="medium",
        age="received 11:02",
        why=(
            "He tried to reach you by phone and could not get through, then followed up in writing "
            "asking for a lunch. A missed call plus an unanswered mail is the combination that "
            "reads as being ignored, so worth a line even if the lunch itself waits."
        ),
        excerpt=(
            "Försökte ringa dig nyss men kom inte fram… Det vore kul att ses över en lunch "
            "framöver om du har tid?"
        ),
        excerpt_source="Jonathan Wintzell — Tue 11:02",
        to=["jonathan@needo.se"],
        cc=[],
        subject="Sv: Ametalis x Needo",
        draft=(
            "Hej Jonathan,\n\n"
            "Tack, och ursäkta att jag inte fångade samtalet - det är fullt just nu.\n\n"
            "Lunch låter bra. Den här veckan är tät, men skicka gärna ett par förslag från nästa "
            "vecka och framåt så löser vi det.\n\n"
            "Mvh, Kim"
        ),
    ),
    Dossier(
        key="ekholm_dates",
        title="Daniel Ekholm — came back with dates, needs you to pick one",
        counterpart="Daniel Ekholm (KPMG)",
        severity="medium",
        age="he answered 18:26 last night · Friday has since gone",
        why=(
            "You answered his lunch request last night and asked when suited him. He offered today "
            "or Friday this week, or Monday–Tuesday next week. Today is nearly gone, and Friday "
            "closed at 13:17 when you gave the slot to Mårten — Friday 21/8 12:00–13:00 is now "
            "his lunch, with the M&A update, Andreas and Mikael's July review either side of it. "
            "So the answer to Daniel is next week."
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
            "Den här veckan blev fullbokad, så låt oss ta nästa vecka istället. Måndag 24/8 kl. "
            "12:00 funkar bra för mig - annars tisdag 25/8, i princip när du vill.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Monday and Tuesday next week are both open at lunch. Monday has an SJC check-in at "
            "14:45, so a Monday lunch is fine but not open-ended."
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
