from dataclasses import dataclass, field
from typing import Literal, Optional

FeedKind = Literal["rss", "atom", "sitemap", "ippsec-json"]

@dataclass(frozen=True)
class FeedSource:
    id: str                       
    name: str                     
    homepage: str
    feed_url: str                
    feed_kind: FeedKind
    coverage_url: Optional[str] = None
    coverage_url_pattern: Optional[str] = None
    kind: str = "writeups"        
    author: Optional[str] = None
    default_tags: tuple = ()      
    default_categories: tuple = ()
    license_note: str = (
        "Metadata only (title, tags, URL). Content is not rehosted; "
        "every result links back to the original author."
    )
    request_delay: float = 2.0 
    enabled: bool = True
    options: dict = field(default_factory=dict)

@dataclass(frozen=True)
class RefSource:
    id: str
    name: str
    homepage: str
    kind: str = "docs"
    author: Optional[str] = None
    license_note: str = "Official documentation; linked for reference, not rehosted."

FEED_SOURCES: list[FeedSource] = [
    FeedSource(
        id="0xdf",
        name="0xdf hacks stuff",
        homepage="https://0xdf.gitlab.io/",
        feed_url="https://0xdf.gitlab.io/feed.xml",
        feed_kind="atom",
        coverage_url="https://0xdf.gitlab.io/sitemap.xml",
        coverage_url_pattern=r"/\d{4}/\d{2}/\d{2}/[^/]+\.html$",
        author="0xdf",
        default_tags=("writeup", "htb"),
        default_categories=("enumeration",),
    ),
    FeedSource(
        id="ippsec",
        name="IppSec",
        homepage="https://ippsec.rocks/",
        feed_url="https://ippsec.rocks/dataset.json",
        feed_kind="ippsec-json",
        author="IppSec",
        default_tags=("video", "htb"),
        default_categories=("enumeration",),
        options={"granularity": "video"},
    ),
]

REF_SOURCES: list[RefSource] = [
    RefSource("nmap-docs", "Nmap Reference Guide", "https://nmap.org/book/man.html", author="Nmap Project"),
    RefSource("manpages", "Linux man pages", "https://man7.org/linux/man-pages/"),
    RefSource("ms-docs", "Microsoft Learn", "https://learn.microsoft.com/windows-server/administration/windows-commands/"),
    RefSource("curl-docs", "curl documentation", "https://curl.se/docs/"),
    RefSource("gnu-docs", "GNU software manuals", "https://www.gnu.org/manual/"),
    RefSource("openbsd-docs", "OpenSSH manual", "https://man.openbsd.org/ssh.1"),
    RefSource("tcpdump-docs", "tcpdump documentation", "https://www.tcpdump.org/manpages/"),
    RefSource("gobuster-repo", "gobuster (GitHub)", "https://github.com/OJ/gobuster"),
]

def all_source_records() -> list[dict]:
    records: list[dict] = []
    for s in FEED_SOURCES:
        records.append({
            "id": s.id, "name": s.name, "author": s.author,
            "homepage": s.homepage, "kind": s.kind, "license_note": s.license_note,
        })
    for r in REF_SOURCES:
        records.append({
            "id": r.id, "name": r.name, "author": r.author,
            "homepage": r.homepage, "kind": r.kind, "license_note": r.license_note,
        })
    return [{k: v for k, v in rec.items() if v is not None} for rec in records]