#!/usr/bin/env python3
"""verify_citations.py - Verify legal citations against CourtListener and CAP APIs.

Usage:
    python3 scripts/verify_citations.py "Ashcroft v. Iqbal, 556 U.S. 662 (2009)"
    python3 scripts/verify_citations.py --file brief.txt
    python3 scripts/verify_citations.py --json '["citation1", "citation2"]'

Environment variables (optional):
    COURTLISTENER_API_KEY  - API key for CourtListener
    CAP_API_KEY            - API key for Caselaw Access Project
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


@dataclass
class CitationResult:
    """Result of a citation verification attempt."""
    citation: str
    verified: bool
    source: Optional[str] = None
    case_name: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


class CitationParser:
    """Parse legal citations into structured components."""

    # Federal reporter pattern: Party v. Party, Vol Reporter Page (Court Year)
    FEDERAL_PATTERN = re.compile(
        r'(.+?)\s*,\s*(\d+)\s+'
        r'(U\.S\.|S\.\s*Ct\.|L\.\s*Ed\.|F\.\d+[a-z]*|F\.\s*Supp\.\s*\d*[a-z]*|B\.R\.)'
        r'\s+(\d+)'
        r'(?:\s*\((.+?)\s+(\d{4})\))?'
    )

    # California state pattern: Party v. Party (Year) Vol Cal.Reporter Page
    CA_STATE_PATTERN = re.compile(
        r'(.+?)\s*\((\d{4})\)\s*(\d+)\s+'
        r'(Cal\.\d*[a-z]*|Cal\.\s*App\.\s*\d*[a-z]*)'
        r'\s+(\d+)'
    )

    # Statute pattern: Title U.S.C. section Number
    STATUTE_PATTERN = re.compile(
        r'(\d+)\s+U\.S\.C\.\s*(?:section|\u00a7)\s*(\d+[a-z]*)'
    )

    @classmethod
    def parse(cls, citation: str) -> dict:
        """Parse a citation string into components."""
        citation = citation.strip().strip('*_')

        m = cls.FEDERAL_PATTERN.search(citation)
        if m:
            return {
                'type': 'case',
                'subtype': 'federal',
                'name': m.group(1).strip(),
                'volume': m.group(2),
                'reporter': m.group(3).strip(),
                'page': m.group(4),
                'court': m.group(5) if m.group(5) else None,
                'year': m.group(6) if m.group(6) else None,
            }

        m = cls.CA_STATE_PATTERN.search(citation)
        if m:
            return {
                'type': 'case',
                'subtype': 'california',
                'name': m.group(1).strip(),
                'year': m.group(2),
                'volume': m.group(3),
                'reporter': m.group(4).strip(),
                'page': m.group(5),
            }

        m = cls.STATUTE_PATTERN.search(citation)
        if m:
            return {
                'type': 'statute',
                'title': m.group(1),
                'section': m.group(2),
            }

        return {'type': 'unknown', 'raw': citation}


class CourtListenerVerifier:
    """Verify citations using the CourtListener API."""

    BASE_URL = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key:
            self.session.headers['Authorization'] = f'Token {api_key}'
        self.session.headers['User-Agent'] = 'LitigationSkill/1.0'

    def search_citation(self, parsed: dict) -> Optional[CitationResult]:
        """Search CourtListener for a parsed citation."""
        if parsed.get('type') != 'case':
            return None

        try:
            params = {
                'citation': f"{parsed['volume']} {parsed['reporter']} {parsed['page']}",
            }
            resp = self.session.get(
                f"{self.BASE_URL}/search/",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get('count', 0) > 0:
                result = data['results'][0]
                return CitationResult(
                    citation=f"{parsed['volume']} {parsed['reporter']} {parsed['page']}",
                    verified=True,
                    source='courtlistener',
                    case_name=result.get('caseName', result.get('case_name', '')),
                    url=f"https://www.courtlistener.com{result.get('absolute_url', '')}",
                )
            return None
        except requests.RequestException as e:
            return CitationResult(
                citation=str(parsed),
                verified=False,
                error=f"CourtListener API error: {e}",
            )


class CAPVerifier:
    """Verify citations using the Caselaw Access Project API."""

    BASE_URL = "https://api.case.law/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key:
            self.session.headers['Authorization'] = f'Token {api_key}'
        self.session.headers['User-Agent'] = 'LitigationSkill/1.0'

    def search_citation(self, parsed: dict) -> Optional[CitationResult]:
        """Search CAP for a parsed citation."""
        if parsed.get('type') != 'case':
            return None

        try:
            params = {
                'cite': f"{parsed['volume']} {parsed['reporter']} {parsed['page']}",
            }
            resp = self.session.get(
                f"{self.BASE_URL}/cases/",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get('results', [])
            if results:
                case = results[0]
                return CitationResult(
                    citation=f"{parsed['volume']} {parsed['reporter']} {parsed['page']}",
                    verified=True,
                    source='cap',
                    case_name=case.get('name_abbreviation', case.get('name', '')),
                    url=case.get('frontend_url', ''),
                )
            return None
        except requests.RequestException as e:
            return CitationResult(
                citation=str(parsed),
                verified=False,
                error=f"CAP API error: {e}",
            )


def extract_citations_from_text(text: str) -> list[str]:
    """Extract potential legal citations from a block of text."""
    patterns = [
        # Federal cases
        r'[A-Z][\w.]+\s+v\.\s+[A-Z][\w.]+,\s*\d+\s+(?:U\.S\.|S\.\s*Ct\.|F\.\d+[a-z]*|F\.\s*Supp\.\s*\d*[a-z]*)\s+\d+\s*\([^)]+\)',
        # California cases
        r'[A-Z][\w.]+\s+v\.\s+[A-Z][\w.]+\s*\(\d{4}\)\s*\d+\s+Cal\.\S+\s+\d+',
    ]
    citations = []
    for pattern in patterns:
        citations.extend(re.findall(pattern, text))
    return list(set(citations))


def verify_citations(citations: list[str], verbose: bool = False) -> list[CitationResult]:
    """Verify a list of citation strings."""
    cl_key = os.environ.get('COURTLISTENER_API_KEY')
    cap_key = os.environ.get('CAP_API_KEY')

    cl = CourtListenerVerifier(cl_key)
    cap = CAPVerifier(cap_key)

    results = []
    for cite_str in citations:
        parsed = CitationParser.parse(cite_str)

        if parsed['type'] == 'statute':
            results.append(CitationResult(
                citation=cite_str,
                verified=False,
                error='Statute verification not yet supported. Manual check recommended.',
            ))
            continue

        if parsed['type'] == 'unknown':
            results.append(CitationResult(
                citation=cite_str,
                verified=False,
                error='Could not parse citation format.',
            ))
            continue

        if verbose:
            print(f"Verifying: {cite_str}", file=sys.stderr)

        # Try CourtListener first
        result = cl.search_citation(parsed)
        if result and result.verified:
            results.append(result)
            time.sleep(0.5)  # rate limit
            continue

        # Fall back to CAP
        result = cap.search_citation(parsed)
        if result and result.verified:
            results.append(result)
            time.sleep(0.5)
            continue

        # Neither found it
        results.append(CitationResult(
            citation=cite_str,
            verified=False,
            error='Citation not found in CourtListener or CAP. Manual verification required.',
        ))
        time.sleep(0.5)

    return results


def main():
    parser = argparse.ArgumentParser(description='Verify legal citations')
    parser.add_argument('citation', nargs='?', help='Single citation to verify')
    parser.add_argument('--file', help='Text file to extract and verify citations from')
    parser.add_argument('--json', help='JSON array of citations to verify')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output-json', action='store_true', help='Output results as JSON')
    args = parser.parse_args()

    citations = []
    if args.citation:
        citations = [args.citation]
    elif args.file:
        with open(args.file, 'r') as f:
            text = f.read()
        citations = extract_citations_from_text(text)
        if not citations:
            print('No citations found in file.')
            sys.exit(0)
        print(f"Found {len(citations)} citation(s) to verify.", file=sys.stderr)
    elif args.json:
        citations = json.loads(args.json)
    else:
        parser.print_help()
        sys.exit(1)

    results = verify_citations(citations, verbose=args.verbose)

    if args.output_json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            status = 'VERIFIED' if r.verified else 'UNVERIFIED'
            print(f"[{status}] {r.citation}")
            if r.case_name:
                print(f"  Case: {r.case_name}")
            if r.source:
                print(f"  Source: {r.source}")
            if r.url:
                print(f"  URL: {r.url}")
            if r.error:
                print(f"  Note: {r.error}")
            print()

    # Exit with error if any citations unverified
    if any(not r.verified for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
