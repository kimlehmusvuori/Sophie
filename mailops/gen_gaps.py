"""Regenerate the follow-up-gaps section of the docket template from docket_data.py.

Single source of truth: the app and the published page now render the same nine
dossiers, so a correction only has to be made once.
"""

import html
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, "/home/user/Sophie/mailops")
from docket_data import DOSSIERS  # noqa: E402

TPL = pathlib.Path(
    "/tmp/claude-0/-home-user-Sophie/003ecc2b-11de-5433-8171-2b444b779cff/scratchpad/mail_docket_template.html"
)

CHIP = {
    "urgent": ("urgent", "Reply today"),
    "high": ("high", "High priority"),
    "medium": ("medium", "Needs an answer"),
}

# Short "found-via" ribbons, keyed by dossier. Absent = no ribbon.
RIBBON = {
    "lars_loi": "New this sync — he asked for it today",
    "filipovic_pfas": "Changed again this sync",
    "andreas_gap": "New this sync",
    "eric_edholm": "New this sync",
    "boregruppen": "Corrected this sync",
    "marcus": "Re-dated this sync",
}


def split_counterpart(text):
    """Render 'Name (Org) · rest' with the parenthetical and tail de-emphasised."""
    return re.sub(
        r"\(([^)]+)\)",
        lambda m: f"<span>({html.escape(m.group(1))})</span>",
        html.escape(text),
    )


def card(d):
    chip_cls, chip_txt = CHIP[d.severity]
    ribbon = RIBBON.get(d.key)
    parts = [
        f'    <div class="dossier sev-{"urgent" if d.severity == "urgent" else d.severity}">',
        '      <div class="dossier-head">',
        "        <div>",
        f'          <p class="dossier-title">{html.escape(d.title)}</p>',
        f'          <p class="dossier-thread">{split_counterpart(d.counterpart)}</p>',
        "        </div>",
        '        <div class="dossier-meta">',
        f'          <span class="chip {chip_cls}">{chip_txt}</span>',
        f'          <span class="open-for">{html.escape(d.age)}</span>',
        "        </div>",
        "      </div>",
        '      <div class="dossier-body">',
    ]
    if ribbon:
        parts.append(f'        <span class="found-via">{html.escape(ribbon)}</span>')
    parts += [
        f'        <p class="why-flagged"><b>Why flagged:</b> {html.escape(d.why)}</p>',
        '        <blockquote class="excerpt">',
        f'          "{html.escape(d.excerpt)}"',
        f"          <cite>{html.escape(d.excerpt_source)}</cite>",
        "        </blockquote>",
        '        <div class="draft-panel">',
        '          <div class="draft-label"><span>Draft reply</span>'
        '<span class="not-sent">Not sent</span></div>',
        f'          <div class="draft-body">{html.escape(d.draft)}</div>',
    ]
    if d.caution:
        parts.append(f'          <p class="draft-note">⚠ {html.escape(d.caution)}</p>')
    parts += ["        </div>", "      </div>", "    </div>", ""]
    return "\n".join(parts)


def main():
    h = TPL.read_text()

    now = subprocess.run(
        ["date", "+%a %d %b %Y, %H:%M"],
        capture_output=True,
        text=True,
        env={"TZ": "Europe/Stockholm", "PATH": "/usr/bin:/bin"},
    ).stdout.strip()
    h = re.sub(r"Synced — [A-Za-z]{3} \d{2} [A-Za-z]{3} 2026, \d{2}:\d{2}", f"Synced — {now}", h)

    # Replace everything from the first dossier card to the end of the section.
    start = h.index("    <!-- Dossier")
    end = h.index("  <!-- ============ SECTION: PRIORITY QUEUE ============ -->")
    tail = h[start:end]
    closer = tail[tail.rindex("  </div>") :]  # keep the section's own closing div
    body = "    <!-- Dossier cards — generated from mailops/docket_data.py -->\n"
    body += "\n".join(card(d) for d in DOSSIERS)
    h = h[:start] + body + closer + h[end:]

    n_gaps = len(DOSSIERS)
    n_hot = sum(1 for d in DOSSIERS if d.severity in ("urgent", "high"))
    h = re.sub(
        r'(<div class="stat-n high">)\d+(</div>\s*<div class="stat-label">Follow-up gaps)',
        rf"\g<1>{n_gaps}\g<2>",
        h,
    )
    h = re.sub(
        r'(<div class="stat-n high">)\d+(</div>\s*<div class="stat-label">High priority)',
        rf"\g<1>{n_hot}\g<2>",
        h,
    )

    TPL.write_text(h)
    print(f"timestamp: {now}")
    n_cards = h.count('class="dossier sev-')
    print(f"cards: {n_cards} / gaps stat: {n_gaps} / hot: {n_hot}")


main()
