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
        key="attest_levels",
        title="Attest levels — Andreas and Mikael are both waiting on your call",
        counterpart="Andreas Bladh & Mikael Nilsson (Ametalis)",
        severity="medium",
        age="Andreas asked 10:57 · Mikael added 16:51",
        why=(
            "Andreas asked this morning what volume levels are reasonable for the attest rights "
            "in the VD-instruktion. This afternoon Mikael came in on the same thread proposing "
            "they keep it simple for now — a light policy plus a power of attorney — and then "
            "land proper documents for VD-instruktion, ägardirektiv and attestordning. Neither "
            "can finish without a direction, and it has been sitting most of the day."
        ),
        excerpt=(
            "Vi kan väl hålla det enkelt typ som vi va inne på för nån vecka sen, enkel policy "
            "eventuellt kombinerat med en fullmakt. Sen behöver vi se till att landa en ordentlig "
            "policy på: vd instruktion / Ägardirektiv / Attestordning"
        ),
        excerpt_source="Mikael Nilsson — Mon 16:51",
        to=["andreas.bladh@ametalis.com", "mikael.nilsson@ametalis.com"],
        cc=[],
        subject="Re: Firmateckning",
        draft=(
            "Hej,\n\n"
            "Enig med Mikael - vi kör en enkel policy nu, eventuellt kombinerad med fullmakt, så "
            "vi inte blockerar löpande ärenden.\n\n"
            "Parallellt landar vi de tre: VD-instruktion, ägardirektiv och attestordning. "
            "Andreas, du driver utkastet.\n\n"
            "Kring attestnivåer vill jag se ett förslag från er två snarare än att jag sätter "
            "siffrorna själv. Ta fram nivåer utifrån vad som faktiskt passerar idag - volym och "
            "typ av beslut - så tar vi ställning utifrån det.\n\n"
            "// Kim"
        ),
        caution=(
            "This delegates the attest levels back to them with a frame rather than answering "
            "Andreas's question directly. If you already have numbers in mind, say them instead."
        ),
    ),
    Dossier(
        key="eric_invoice",
        title="Eric's August invoice — two questions blocking him",
        counterpart="Eric Edholm (consultant)",
        severity="medium",
        age="received 16:54",
        why=(
            "Eric wants to invoice for August and needs two facts first: which legal entity to "
            "bill, and which address to send it to. He cannot proceed without an answer, and he "
            "is the constrained resource in the AI work — worth not leaving him on admin."
        ),
        excerpt=(
            "Tänkte fakturera augusti 💸 Ska jag ställa ut fakturan mot Ametalis AB? Och ska den "
            "skickas till någon speciell email?"
        ),
        excerpt_source="Eric Edholm — Mon 16:54",
        to=["eric@ericgustaf.com"],
        cc=["mikael.nilsson@ametalis.com"],
        subject="Re: Faktura",
        draft=(
            "Hej Eric,\n\n"
            "Ja, ställ den mot Ametalis AB.\n\n"
            "Jag sätter Mikael på cc - han ger dig rätt fakturaadress så den går rätt in i "
            "systemet direkt.\n\n"
            "// Kim"
        ),
        caution=(
            "Confirms Ametalis AB as the billed entity — check that's right if any of the work sat "
            "under a portfolio company. The invoice address is left to Mikael, not guessed."
        ),
    ),
    Dossier(
        key="syntari",
        title="Syntari — Philip has delivered the recommendation you asked for",
        counterpart="Philip Hygrell (Ametalis)",
        severity="urgent",
        age="arrived 15:27 · you asked for this at 09:58",
        why=(
            "This morning you asked Philip for a short recommendation on Syntari so the two of "
            "you could align internally before answering them. He recommends putting it on ice — "
            "partly because he thinks Ametalis can build much of the same thing with Eric, but "
            "mainly because he doubts the portfolio companies are ready to migrate off their "
            "existing systems now. He ends with two direct questions, so nothing moves until you "
            "answer. Syntari (Rafi, Jennifer, Dan) have been waiting on a meeting date since "
            "13 August."
        ),
        excerpt=(
            "Största anledningen är dock att jag är osäker på om våra bolag är redo för en stor, "
            "gemensam, satsning i dagsläget… Vad tänker du? Hur vill du att jag svarar?"
        ),
        excerpt_source="Philip Hygrell — Mon 15:27",
        to=["philip.hygrell@ametalis.com"],
        cc=[],
        subject="Sv: Syntari x Ametalis",
        draft=(
            "Hej Philip,\n\n"
            "Tack - bra och tydlig analys, och jag delar din bild. Vi lägger Syntari på is för "
            "nu. Huvudskälet för mig är samma som ditt: bolagen är inte redo för en gemensam "
            "systemflytt i det här läget, och då blir det fel att dra igång.\n\n"
            "Innan du svarar dem tar vi 15 min så vi är överens om budskapet - lägg in en tid "
            "imorgon.\n\n"
            "Mot Syntari vill jag att vi är vänliga men tydliga: vi pausar, vi stänger inte "
            "dörren, och vi återkommer när vi ser att bolagen har kapacitet.\n\n"
            "// Kim"
        ),
        caution=(
            "This draft commits to pausing Syntari. That is your call, not Philip's — read his "
            "reasoning before sending."
        ),
    ),
    Dossier(
        key="ekholm",
        title="Daniel Ekholm (KPMG) — lunch request unanswered",
        counterpart="Daniel Ekholm (KPMG)",
        severity="medium",
        age="received 13:37 today",
        why=(
            "Daniel worked with you on project Matteus during your Norvestor years and is asking "
            "for a lunch in the coming weeks. Small ask, easy to lose in a busy inbox — flagged "
            "now rather than after it has aged a week."
        ),
        excerpt=(
            "Var ett bra tag sen vi jobbade tillsammans på projekt Matteus (när du var på "
            "Norvestor), vad sägs om att ta en lunch de kommande veckorna?"
        ),
        excerpt_source="Daniel Ekholm — Mon 13:37",
        to=["daniel.ekholm@kpmg.se"],
        cc=[],
        subject="Re: Lunch",
        draft=(
            "Hej Daniel,\n\n"
            "Kul att höra från dig! Sommaren var bra, tack - hoppas detsamma för dig.\n\n"
            "Lunch låter bra. Skicka gärna ett par förslag på dagar de kommande veckorna, så ser "
            "jag vad som funkar.\n\n"
            "Mvh,\n"
            "Kim"
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
