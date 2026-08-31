#!/usr/bin/env python3
"""Generate self-contained SMIL cards from a public GitHub avatar/calendar.

Run from the profile repository: python scripts/generate_profile.py
Requires Pillow. No token needed. Fails rather than inventing contribution data.
Use --static to produce a motion-free edition. No external SVG dependencies.
"""
import argparse
import io
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from PIL import Image, ImageOps

BG, FG, MUTED = "#0d1117", "#e6edf3", "#8b9aae"
CYAN, GREEN, ORANGE, PURPLE = "#67e8f9", "#7ee787", "#ffa657", "#c4a5ff"
COLORS = ["#19232e", "#0e4429", "#006d32", "#26a641", "#39d353"]
START, END = "<!-- PREMIUM-PROFILE:START -->", "<!-- PREMIUM-PROFILE:END -->"

def fetch(url):
    req = Request(url, headers={"User-Agent": "GitHub-Profile-Card/1.0"})
    with urlopen(req, timeout=40) as response:
        return response.read()

def txt(x,y,value,color=FG,size=12,attrs=""):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {attrs}>{escape(str(value))}</text>'

def fade(delay, static, duration=.45):
    if static:
        return ""
    return (f'<animate attributeName="opacity" values="0;0" begin="0s" dur="{delay:.3f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" values="0;1" begin="{delay:.3f}s" dur="{duration}s" fill="freeze"/>')

def shell(w,h,title,body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">Saurabh Jaju: Java, Spring Boot, enterprise systems and AI-assisted engineering. Self-contained animated SVG.</desc>
<defs>
 <linearGradient id="glass" x2="1" y2="1"><stop stop-color="#182333"/><stop offset=".55" stop-color="#101923"/><stop offset="1" stop-color="#0d1117"/></linearGradient>
 <linearGradient id="edge" x2="1" y2="1"><stop stop-color="{CYAN}" stop-opacity=".65"/><stop offset=".5" stop-color="{PURPLE}" stop-opacity=".18"/><stop offset="1" stop-color="{GREEN}" stop-opacity=".4"/></linearGradient>
 <radialGradient id="aura"><stop stop-color="#22d3ee" stop-opacity=".15"/><stop offset="1" stop-color="#22d3ee" stop-opacity="0"/></radialGradient>
 <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 3.5H4" stroke="#fff" stroke-opacity=".025"/></pattern>
</defs>
<rect width="{w}" height="{h}" rx="18" fill="{BG}"/>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="url(#glass)" stroke="url(#edge)"/>
<ellipse cx="{w*.8}" cy="115" rx="{w*.55}" ry="220" fill="url(#aura)"/>
<rect x="2" y="2" width="{w-4}" height="{h-4}" rx="17" fill="url(#scan)"/>
<g font-family="Consolas, Menlo, monospace">{body}</g></svg>'''

def header(label):
    return (''.join(f'<circle cx="{24+i*18}" cy="25" r="5" fill="{c}"/>' for i,c in enumerate(["#ff5f57","#febc2e","#28c840"]))
            +txt(91,29,label,MUTED,10)
            +'<path d="M20 49H500" stroke="#ffffff" stroke-opacity=".08"/>')

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-date" in attrs and "data-level" in attrs:
            level = int(attrs["data-level"])
            if level not in range(5):
                raise ValueError("Unexpected contribution level")
            self.days[date.fromisoformat(attrs["data-date"])] = level

def calendar(username):
    parser = CalendarParser()
    parser.feed(fetch(f"https://github.com/users/{username}/contributions").decode())
    if len(parser.days) < 300:
        raise RuntimeError("GitHub calendar markup changed or data unavailable; no synthetic data generated.")
    last = max(parser.days)
    sunday = last-timedelta(days=(last.weekday()+1)%7)
    first = sunday-timedelta(weeks=52)
    return [[(first+timedelta(days=col*7+row), parser.days.get(first+timedelta(days=col*7+row)))
             for row in range(7)] for col in range(53)]

def graph(weeks,static):
    parts=[txt(30,34,"THE BUILD SIGNAL",FG,17,'letter-spacing="2"'),
           txt(30,55,"PUBLIC CONTRIBUTION CALENDAR / 53 WEEKS",MUTED,10)]
    for row,label in [(1,"MON"),(3,"WED"),(5,"FRI")]:
        parts.append(txt(27,91+row*19,label,MUTED,9))
    for col,week in enumerate(weeks):
        for row,(day,level) in enumerate(week):
            x,y=68+col*18,79+row*19
            delay=.18+col*.035+(6-row)*.075
            color=COLORS[level] if level is not None else "#101721"
            effect=' filter="url(#glow)"' if level is not None and level>=3 else ""
            label=f"{day.isoformat()} / contribution level {level}" if level is not None else "Outside reported range"
            parts.append(f'<g>{fade(delay,static)}<title>{label}</title><rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{color}"{effect}/>')
            if not static and level is not None:
                parts.append(f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="#edfff4" opacity="0"><animate attributeName="opacity" values="0;1;.25;0" keyTimes="0;.18;.55;1" begin="{delay:.3f}s" dur=".5s" fill="freeze"/></rect>')
            parts.append('</g>')
    parts += [txt(30,248,"SMALL COMMITS. COMPOUNDING IMPACT.",CYAN,10),
              txt(30,270,f"Snapshot: {date.today().isoformat()} / actual public GitHub levels",MUTED,9),
              txt(870,248,"LESS",MUTED,9)]
    for i,c in enumerate(COLORS):
        parts.append(f'<rect x="{905+i*18}" y="237" width="12" height="12" rx="2" fill="{c}"/>')
    parts.append(txt(1000,248,"MORE",MUTED,9))
    return shell(1060,294,"Saurabh Jaju — public contribution calendar","".join(parts))

def reveal_clip(ident,x,y,width,height,delay,duration,static,steps=None):
    animations=""
    if not static:
        values=f"0;{width}" if not steps else ";".join(str(round(width*i/steps,2)) for i in range(steps+1))
        mode=' calcMode="discrete"' if steps else ""
        animations=(f'<animate attributeName="width" values="0;0" begin="0s" dur="{delay:.3f}s" fill="freeze"/>'
                    f'<animate attributeName="width" values="{values}" begin="{delay:.3f}s" dur="{duration:.3f}s" fill="freeze"{mode}/>')
    return f'<defs><clipPath id="{ident}" clipPathUnits="userSpaceOnUse"><rect x="{x}" y="{y}" width="{width}" height="{height}">{animations}</rect></clipPath></defs>'

def portrait(raw,name,static):
    cols,rows=80,48
    with Image.open(io.BytesIO(raw)) as image:
        fitted=ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"),(880,806),method=Image.Resampling.LANCZOS)
        gray=ImageOps.autocontrast(ImageOps.grayscale(fitted)).resize((cols,rows),Image.Resampling.LANCZOS)
    pixels=list(gray.get_flattened_data()) if hasattr(gray,"get_flattened_data") else list(gray.getdata())
    ramp=" .,:;irsXA253hMHGS#9B&@"
    parts=[header("identity.sh / saurabh"),txt(34,75,"RENDERING HUMAN / NOT A TEMPLATE",MUTED,9)]
    for row in range(rows):
        line="".join(ramp[pixels[row*cols+col]*(len(ramp)-1)//255] for col in range(cols))
        x,y,width=34,98+row*8.4,448
        delay=.25+row*.055
        ident=f"ascii-{row}"
        parts.append(reveal_clip(ident,x,y-8,width,11,delay,.055,static))
        parts.append(txt(x,y,line,[CYAN,GREEN,"#79c0ff"][(row//16)%3],8.6,
                         f'xml:space="preserve" textLength="{width}" lengthAdjust="spacingAndGlyphs" clip-path="url(#{ident})"'))
        if not static:
            parts.append(f'<rect x="{x}" y="{y-7}" width="6" height="9" fill="#fff" opacity="0"><animate attributeName="x" values="{x};{x+width}" begin="{delay:.3f}s" dur=".055s" fill="freeze"/><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.01;.99;1" begin="{delay:.3f}s" dur=".055s" fill="freeze"/></rect>')
    parts.append('<path d="M28 515H492" stroke="#303c4e"/>')
    for ident,value,y,delay,color in [("cmd","$ whoami",540,3.1,GREEN),("name",name,568,3.9,FG)]:
        width=len(value)*8.5
        parts.append(reveal_clip(ident,34,y-16,width,22,delay,.65,static,len(value)))
        parts.append(txt(34,y,value,color,14,f'clip-path="url(#{ident})" textLength="{width}" lengthAdjust="spacingAndGlyphs"'))
    return shell(520,600,f"{name} — animated ASCII portrait","".join(parts))

def info(username,name,static):
    lines=[
      (username+"@github",CYAN,15),
      ("-------------------------------------",MUTED,12),
      ("01 / ABOUT",ORANGE,11),
      (name,FG,19),
      ("Senior Software Engineer",FG,13),
      ("Dubai, UAE / Emirates Group IT",MUTED,12),
      ("",FG,12),
      ("02 / STACK", "#79c0ff",11),
      ("Java / Spring Boot / Angular",FG,13),
      ("Microservices / REST APIs",CYAN,13),
      ("AWS / Docker / Kubernetes",FG,13),
      ("CI/CD / DevSecOps / AI tooling",PURPLE,13),
      ("",FG,12),
      ("03 / HIGHLIGHTS",GREEN,11),
      ("10+ years in software engineering",FG,12),
      ("Enterprise + aviation technology",ORANGE,12),
      ("Modernization + reliable delivery",FG,12),
      ("AI-assisted engineering",CYAN,12),
      ("",FG,12),
      ("$ build --with-purpose",GREEN,13),
    ]
    parts=[header("neofetch / engineer")]
    for i,(value,color,size) in enumerate(lines):
        delay=.15+i*.06
        parts.append(f'<g>{fade(delay,static)}')
        if not static:
            parts.append(f'<animateTransform attributeName="transform" type="translate" values="0 9;0 0" begin="{delay:.3f}s" dur=".45s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".16 1 .3 1"/>')
        parts.append(txt(32,86+i*23,value,color,size))
        parts.append('</g>')
    parts.append('<path d="M28 555H492" stroke="#303c4e"/>')
    parts.append(txt(32,578,"SYSTEM READY",MUTED,9,'letter-spacing="2"'))
    for i,c in enumerate([ORANGE,"#79c0ff",GREEN,CYAN,PURPLE,FG]):
        parts.append(f'<rect x="{358+i*22}" y="566" width="16" height="12" rx="3" fill="{c}"/>')
    return shell(520,600,f"{name} — engineering profile","".join(parts))


def banner(static):
    parts=[txt(42,51,"SAURABH JAJU",FG,31,'letter-spacing="4"'),
           txt(43,81,"SOFTWARE DEPTH. SYSTEMS THINKING.",CYAN,12,'letter-spacing="2"'),
           txt(43,107,"Java / Enterprise architecture / Aviation / AI-assisted engineering",MUTED,11)]
    for i,(value,color) in enumerate([("BUILD",CYAN),("MODERNIZE",ORANGE),("DELIVER",GREEN)]):
        x=650+i*128
        parts.append(f'<g>{fade(.1+i*.18,static)}<rect x="{x}" y="43" width="113" height="46" rx="10" fill="#12202b" stroke="{color}" stroke-opacity=".4"/>')
        parts.append(txt(x+12,71,value,color,11))
        parts.append('</g>')
    parts.append('<path d="M42 133H1018" stroke="#263648"/>')
    if not static:
        parts.append('<rect x="42" y="132" width="90" height="2" rx="1" fill="#67e8f9" opacity=".65"><animate attributeName="x" values="42;928;42" dur="9s" repeatCount="indefinite"/></rect>')
    return shell(1060,160,"Saurabh Jaju — software engineer","".join(parts))

def story(static):
    panels=[
      ("01 / ENGINEERING FOCUS",CYAN,[
        "Enterprise & aviation platforms","Legacy-to-microservice modernization",
        "Secure APIs & integration","Testing, quality gates & observability",
        "Technical leadership & mentoring"]),
      ("02 / TOOLKIT",PURPLE,[
        "Java / Spring Boot / REST / SOAP","Angular / Python / distributed systems",
        "AWS / Docker / Kubernetes","GitLab CI/CD / Postman / Kibana",
        "AI-assisted review & repository analysis"]),
      ("03 / SELECTED PROJECTS",ORANGE,[
        "SpringBootRestApiWithAngular","eds-starter6-jpa",
        "angular-electron","TestApp",
        "Explore repositories via the links below"]),
    ]
    parts=[txt(32,37,"ENGINEERING / IN MOTION",FG,15,'letter-spacing="2"')]
    for index,(title,color,lines) in enumerate(panels):
        x=26+index*346
        parts.append(f'<rect x="{x}" y="59" width="330" height="227" rx="13" fill="#101a25" stroke="{color}" stroke-opacity=".22"/>')
        parts.append(txt(x+17,89,title,color,11))
        for row,value in enumerate(lines):
            delay=.15+index*.12+row*.09
            parts.append(f'<g>{fade(delay,static)}')
            if not static:
                parts.append(f'<animateTransform attributeName="transform" type="translate" values="0 6;0 0" begin="{delay:.3f}s" dur=".5s" fill="freeze"/>')
            parts.append(txt(x+17,122+row*29,value,FG if row%2==0 else MUTED,10.5))
            parts.append('</g>')
        parts.append(f'<rect x="{x+17}" y="272" width="296" height="2" fill="{color}" opacity=".2"/>')
        if not static:
            parts.append(f'<rect x="{x+17}" y="272" width="36" height="2" fill="{color}" opacity=".8"><animate attributeName="x" values="{x+17};{x+277};{x+17}" dur="{7+index}s" repeatCount="indefinite"/></rect>')
    parts.append(txt(32,322,"RELIABILITY IS A FEATURE. CLARITY IS A SKILL.",GREEN,10,'letter-spacing="1"'))
    return shell(1060,346,"Engineering focus, toolkit and selected projects","".join(parts))

def integrate(root):
    path=root/"README.md"
    content=path.read_text(encoding="utf-8") if path.exists() else ""
    block=START+"""
<p align="center"><img src="./assets/profile/profile-banner.svg" width="100%" alt="Saurabh Jaju — software depth, systems thinking"/></p>
<table><tr>
<td width="50%"><img src="./assets/profile/terminal-card.svg" width="100%" alt="Saurabh Jaju — animated ASCII portrait"/></td>
<td width="50%"><img src="./assets/profile/info-card.svg" width="100%" alt="About Saurabh Jaju, stack, and highlights"/></td>
</tr></table>
<p align="center"><img src="./assets/profile/engineering-story.svg" width="100%" alt="Engineering focus, toolkit and selected projects"/></p>
<p align="center"><img src="./assets/profile/github-contribution-animation.svg" width="100%" alt="Actual public GitHub contribution levels, animated diagonally"/></p>
"""+END
    if content.count(START)!=content.count(END) or content.count(START)>1:
        raise RuntimeError("Malformed README markers; no README changes made.")
    if START in content:
        before,after=content.split(START,1)
        _,after=after.split(END,1)
        content=before+block+after
    else:
        content=content.rstrip()+"\n\n"+block+"\n"
    path.write_text(content,encoding="utf-8")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--username",default="saurabhjaju2418")
    parser.add_argument("--name",default="Saurabh Jaju")
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--static",action="store_true")
    args=parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}",args.username):
        parser.error("Invalid GitHub username.")
    weeks=calendar(args.username)
    avatar=fetch(f"https://github.com/{args.username}.png?size=512")
    outputs={
      "profile-banner.svg":banner(args.static),
      "engineering-story.svg":story(args.static),
      "terminal-card.svg":portrait(avatar,args.name,args.static),
      "info-card.svg":info(args.username,args.name,args.static),
      "github-contribution-animation.svg":graph(weeks,args.static)
    }
    target=args.root/"assets"/"profile"
    for svg in outputs.values():
        ET.fromstring(svg)
    target.mkdir(parents=True,exist_ok=True)
    for filename,svg in outputs.items():
        (target/filename).write_text(svg,encoding="utf-8")
    integrate(args.root)
    print("Generated and XML-validated 5 self-contained SVGs using real public contributions.")

if __name__=="__main__":
    main()
