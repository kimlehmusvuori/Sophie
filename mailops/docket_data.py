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
        key="lars_loi",
        title="Lars Aaen wants the LOI markups today — B&H meeting is tomorrow 13:00",
        counterpart="Lars Aaen (CEO, Aaen Consult) · cc Niclas Jensen (B&H)",
        severity="urgent",
        age="arrived 15:29 · he asked for it today",
        why=(
            "He tried your mobile and could not reach you, then wrote. Two things in one mail: he "
            "is still waiting on your markups to the LOI after the shareholder discussion, and he "
            "confirms a meeting at Bøgh & Helstrup in Copenhagen at 13:00 CET tomorrow. He asks "
            "explicitly for the marked-up LOI today so his side can go through it internally "
            "before you meet. You told him Mon/Tue, and Tuesday afternoon is now here. Niclas "
            "Jensen at B&H is on copy, so the promise is visible to the counterparty too."
        ),
        excerpt=(
            "It would be world class if we can receive LOI incl. markup´s today, so that we can "
            "discuss it on beforehand internally with our shareholders, before we meet tomorrow."
        ),
        excerpt_source="Lars Aaen — Tue 15:29",
        to=["lars@aaen-consult.dk"],
        cc=["nj@bhbr.dk"],
        subject="Re: LOI and meeting tomorrow",
        draft=(
            "Hi Lars,\n\n"
            "Apologies for the missed calls - it has been a full day.\n\n"
            "You will have our markups this evening. I am in a call until 18:00 CET and will send "
            "them straight after, so your shareholders have them well before we meet.\n\n"
            "And yes - 13:00 tomorrow at Bøgh & Helstrup works. Looking forward to it.\n\n"
            "Best regards,\n"
            "Kim"
        ),
        caution=(
            "This commits you to sending the markups tonight, after the 16:30-18:00 Thy SPA call. "
            "If the shareholder discussion has not actually concluded, change the sentence rather "
            "than the deadline - a second slipped promise on this thread is worse than saying "
            "tomorrow morning. Note also that neither this meeting nor the flights are on your "
            "calendar."
        ),
    ),
    Dossier(
        key="filipovic_pfas",
        title="PFAS reference — Relement is bidding the same tender",
        counterpart="Marko Filipovic (Sellén Filipovic) · via Linus Nilsson, Relement",
        severity="urgent",
        age="Emma handed it to you by name at 15:17, in front of Marko",
        why=(
            "You told Marko at 11:12 that you thought the group had the references and would come "
            "back asap, then forwarded the request to Relement and Envima. Six minutes later Linus "
            "answered: Relement is bidding on the same MCF procurement themselves, with all the "
            "competencies and references in-house. Supplying a reference would be arming a rival "
            "bid against your own portfolio company. You then settled it internally: at 14:54 you "
            "asked Fredric and Linus whether they had it covered, Fredric confirmed at 14:58 that "
            "they need no outside resources to bid, and at 14:59 you wished them luck. So the "
            "decision is made — Ametalis backs Relement's own bid. What is left is telling Marko. "
            "Emma cleared the rest of the group for him at 14:06, Marko corrected the scale at "
            "15:12 (>500 TSEK, not 5 MSEK), and at 15:17 Emma wrote back that Relement might have "
            'something after all and "lämnar den till dig @Kim Lehmusvuori" — in front of Marko. '
            "The thread is now waiting on you by name, and only you know the answer is no."
        ),
        excerpt=(
            "Ah, ok! Jaa, då är det ju lite mindre uppdragsomfång. Då kanske Relement har något "
            "att komma med. 😊 Lämnar den till dig @Kim Lehmusvuori."
        ),
        excerpt_source="Emma Karlsson to Marko, you on Cc — Tue 15:17",
        to=["marko@sellenfilipovic.se"],
        cc=["emma.karlsson@envima.se", "anna.lindberg@envima.se"],
        subject="Re: Referens till en större upphandling",
        draft=(
            "Hej Marko,\n\n"
            "Emma har redan svarat dig om Envima och de andra bolagen, så jag tar den sista "
            "biten.\n\n"
            "Relement lämnar anbud på samma upphandling själva och har kompetenserna och "
            "referenserna in-house - jag har dubbelkollat med dem idag. Då kan jag inte gå in och "
            "stötta ett konkurrerande anbud med referenser, det vore inte rätt mot dem. Så du "
            "behöver inte vänta på mer från vår sida i den här.\n\n"
            "Ursäkta att jag gav dig en annan bild i morse, innan jag hade kollat. Hör gärna av "
            "dig i andra sammanhang, det finns mycket annat vi kan prata om.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Emma and Anna are on Cc so Emma sees it closed - she has just told Marko Relement "
            "might have something. Separately, her first mail told an outside party that Relement "
            "was newly acquired into the group. Worth a word with her, but not in this reply."
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
            "Both August dates are now gone: the 19th is your Copenhagen day (B&H at 13:00, Norion "
            "at 16:00) and the 20th is the Envima board strategy day, 09:00-16:00. Since he has no "
            "further travel days in August, 1 September from 15:00 is the only date left — which "
            "makes the six days of silence costlier than it looked. There is also an outstanding "
            "promise of the digitalisation draft, and a stated wish to meet before the 9 September "
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
            "Tyvärr funkar ingen av augustidagarna för mig - den 19:e är jag i Köpenhamn och den "
            "20:e sitter jag i styrelsemöte hela dagen. Så låt oss ta 1 september från 15:00, då "
            "är jag i Stockholm och har gott om tid.\n\n"
            "Din genomgång av viltkamera-lösningen var intressant. Jag delade den med Mikael, "
            "och hans bild är att AI-delen redan fungerar bra för art och antal - individnivå är "
            "det som skulle vara nytt. Vi tar det vidare när vi ses.\n\n"
            "Inför strategidagen den 9 september skickar jag ut materialet senast en vecka "
            "innan, så det vore värdefullt att ha hunnit prata före dess.\n\n"
            "Mvh,\n"
            "Kim"
        ),
        caution=(
            "Goes straight to 1 September because both August dates are genuinely blocked. That is "
            "eight days before the strategy day, so the digitalisation draft you still owe him "
            "should not wait for the meeting."
        ),
    ),
    Dossier(
        key="boregruppen",
        title="Boregruppen — now collides with Norion on Wednesday",
        counterpart="Jens Waldorff (W+) · cc Maximus Ståel von Holstein",
        severity="urgent",
        age="Wednesday is tomorrow · none of it is on your calendar",
        why=(
            "Correcting an earlier reading of this. Bjørn sent the Norion invitation at 22:35 last "
            "night and Jens forwarded it at 22:39 — Wednesday 16:00–16:55 at their premises — but "
            "it came as an .ics attachment addressed to Jens, so it is not on your calendar and "
            "the mail is still unread. Neither is the 13:00 Bøgh & Helstrup meeting Lars just "
            "confirmed. Your whole Copenhagen Wednesday exists only in other people's inboxes, "
            "while an 11:00-11:30 Implement call still sits on your calendar. Jens had pencilled "
            "Boregruppen (Tonny) for the same Wednesday around 4pm, which Norion now occupies, and "
            "he has not been told. Your 14 August question also remains unanswered: you asked for "
            "Boregruppen's revenue split because drilling operations and non-advisory contractor "
            "work may make it a poor fit."
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
            "Thanks - noted, Norion Wednesday 16:00-16:55 at their place.\n\n"
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
            "None of Wednesday is on your Outlook calendar - not B&H at 13:00, not Norion at "
            "16:00, not the flights. The 11:00-11:30 Implement call still is, and you cannot "
            "take that from a plane. Worth blocking the day before you answer Jens."
        ),
    ),
    Dossier(
        key="andreas_gap",
        title="Andreas's GAP analysis lands two days before the Envima board strategy day",
        counterpart="Andreas Bladh · to you and Mikael Nilsson",
        severity="high",
        age="arrived 15:22 · board meeting is Thursday",
        why=(
            "He has mapped Envima's strategy input against your Ametalis strategy documents and "
            "asks whether you share the take-aways. The substance is pointed: Envima's \"perfekta "
            'kompanjonen" framing is broader than Ametalis wants, integration should be selective '
            "rather than standard, and the growth model needs a revenue-quality filter - he cites "
            "11.8 MSEK revenue and 0.1 MSEK EBITA to July, LTM 22.4 MSEK at an 11% margin against "
            "17% a year earlier, and a 69% billing rate. He ends by recommending a board answer to "
            '"broad companion or most trusted specialist partner". The timing is what makes this '
            "urgent rather than reflective: the Envima styrelsemöte STRATEGI is Thursday 20 "
            "August, 09:00-16:00, and you are on it."
        ),
        excerpt=(
            "Vill Envima vara en bred kompanjon till SME-företag - eller SME-segmentets mest "
            "betrodda specialistpartner inom miljö och compliance? För att säkerställa "
            "samstämmighet med Ametalis rekommenderar jag det senare alternativet."
        ),
        excerpt_source="Andreas Bladh — Tue 15:22",
        to=["andreas.bladh@ametalis.com"],
        cc=["mikael.nilsson@ametalis.com"],
        subject="Sv: tar tacksamt emot reflektioner och tankar från er på nedan GAP-analys",
        draft=(
            "Hej Andreas,\n\n"
            "Bra genomlysning, och slutfrågan är rätt ställd.\n\n"
            "Jag återkommer med kommentarer i detalj, men en sak behöver vi lösa först: Envimas "
            "styrelsemöte om strategi är på torsdag 09:00-16:00 och jag sitter med. Ska den här "
            "mappningen in där - och i så fall som ditt underlag eller som gruppens position? Det "
            "avgör hur jag formulerar mig på mötet.\n\n"
            "Mikael, hör gärna av dig med din syn på intäktskvalitet och debiteringsgrad. Det är "
            "den delen jag tror bär mest, och siffrorna bör stämmas av mot dina innan de används i "
            "ett styrelserum.\n\n"
            "// Kim"
        ),
        caution=(
            "Deliberately does not answer the broad-companion-versus-specialist question for you - "
            "that is your call and Andreas has already recommended one side. The reply settles "
            "sequencing instead, which is the part that expires on Thursday."
        ),
    ),
    Dossier(
        key="eric_edholm",
        title="Eric Edholm offered to meet in Stockholm tomorrow — you are in Copenhagen",
        counterpart="Eric Edholm",
        severity="medium",
        age="arrived 15:07",
        why=(
            "He asks who won the AI outing, whether you should talk priorities and the plan ahead "
            "this week, and offers to meet in person since he is in Stockholm tomorrow - otherwise "
            "a phone call. Tomorrow is your Copenhagen day, so the in-person option has to be "
            "declined rather than left hanging while it is still useful to him."
        ),
        excerpt=(
            "Ska vi snacka lite mer om prioriteringar och planen framåt i veckan? Jag är i "
            "Stockholm imorgon om du har tid så vi snackas IRL. Annars bokar vi ngt på telefon!"
        ),
        excerpt_source="Eric Edholm — Tue 15:07",
        to=["eric@ericgustaf.com"],
        cc=[],
        subject="Re: AI Outing - Top 3 takeaways",
        draft=(
            "Hej Eric,\n\n"
            "Imorgon är jag i Köpenhamn, så IRL får bli en annan gång - synd, hade varit kul.\n\n"
            "Vi tar telefon istället. Fredag efter lunch eller måndag funkar för mig, säg vad som "
            "passar dig bäst.\n\n"
            "// Kim"
        ),
        caution=(
            "He also asked who won the AI outing - add that line yourself, it is not in the thread."
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
