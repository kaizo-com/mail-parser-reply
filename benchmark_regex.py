#!/usr/bin/env python3
"""
Benchmark script to profile regex performance in mailparser_reply.
Tests current patterns against sample email data to identify bottlenecks.
"""
import re
import time
import statistics
from typing import Dict, List, Tuple
import os
import sys

# Add project root to path
base_path = os.path.realpath(os.path.dirname(__file__))
sys.path.append(base_path)

from mailparser_reply.constants import MAIL_LANGUAGES, QUOTED_REGEX, QUOTED_REMOVAL_REGEX, QUOTED_MATCH_INCLUDE, OUTLOOK_MAIL_SEPARATOR, GENERIC_MAIL_SEPARATOR, DEFAULT_SIGNATURE_REGEX

def load_test_emails() -> List[str]:
    """Load test email content from test directory."""
    emails = []
    test_dir = os.path.join(base_path, "test", "emails")
    
    if not os.path.exists(test_dir):
        # Create some sample test data if directory doesn't exist
        sample_emails = [
            """From: test@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000

This is a test email body.

Best regards,
John Doe

On 2024-01-01, at 11:00 AM, jane@example.com wrote:
> This is a quoted reply
> with multiple lines
""",
            """From: user@company.com
To: recipient@example.com
Subject: Re: Meeting Tomorrow

Hi there,

Thanks for the update.

--
Sent from my iPhone

On Jan 1, 2024, at 2:00 PM, Boss <boss@company.com> wrote:
> Can we meet tomorrow at 3pm?
> Let me know if that works.
""",
            """De: sender@test.de
Enviado: Montag, 1. Januar 2024 15:30
Para: receiver@test.de
Asunto: Aw: Projekt Update

Hallo,

Das sieht gut aus.

Mit freundlichen Grüßen
Max Mustermann

Am 01.01.2024 um 14:00 schrieb Team Lead <lead@test.de>:
> Hier ist das Update zum Projekt.
> Bitte prüfen Sie die Änderungen.
"""
        ]
        return sample_emails
    
    # Load actual test files
    for filename in os.listdir(test_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(test_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    emails.append(f.read())
            except Exception:
                continue
    
    return emails if emails else [sample_emails[0]]  # Fallback

def benchmark_pattern(pattern: str, texts: List[str], iterations: int = 100) -> Tuple[float, int]:
    """Benchmark a regex pattern against test texts."""
    compiled_pattern = re.compile(pattern, re.MULTILINE | re.DOTALL)
    times = []
    match_count = 0
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        for text in texts:
            matches = compiled_pattern.findall(text)
            match_count += len(matches)
        end_time = time.perf_counter()
        times.append(end_time - start_time)
    
    avg_time = statistics.mean(times)
    return avg_time, match_count // iterations

def benchmark_all_patterns() -> Dict[str, Dict[str, float]]:
    """Benchmark all regex patterns in constants.py."""
    emails = load_test_emails()
    results = {}
    
    print(f"Benchmarking with {len(emails)} test emails...")
    
    # Test basic patterns
    basic_patterns = {
        'QUOTED_REGEX': QUOTED_REGEX,
        'QUOTED_REMOVAL_REGEX': QUOTED_REMOVAL_REGEX,
        'QUOTED_MATCH_INCLUDE': QUOTED_MATCH_INCLUDE,
        'OUTLOOK_MAIL_SEPARATOR': OUTLOOK_MAIL_SEPARATOR,
        'GENERIC_MAIL_SEPARATOR': GENERIC_MAIL_SEPARATOR,
        'DEFAULT_SIGNATURE_REGEX': DEFAULT_SIGNATURE_REGEX,
    }
    
    print("\n=== Basic Patterns ===")
    for name, pattern in basic_patterns.items():
        try:
            avg_time, matches = benchmark_pattern(pattern, emails)
            results[name] = {'avg_time_ms': avg_time * 1000, 'matches': matches}
            print(f"{name:25s}: {avg_time*1000:8.3f}ms avg, {matches:3d} matches")
        except Exception as e:
            print(f"{name:25s}: ERROR - {e}")
            results[name] = {'avg_time_ms': float('inf'), 'matches': 0}
    
    # Test language-specific patterns
    print(f"\n=== Language-Specific Patterns ===")
    for lang, patterns in MAIL_LANGUAGES.items():
        print(f"\n--- {lang.upper()} ---")
        lang_results = {}
        
        for pattern_type, pattern in patterns.items():
            if isinstance(pattern, str):
                try:
                    avg_time, matches = benchmark_pattern(pattern, emails)
                    lang_results[pattern_type] = {'avg_time_ms': avg_time * 1000, 'matches': matches}
                    print(f"  {pattern_type:15s}: {avg_time*1000:8.3f}ms avg, {matches:3d} matches")
                except Exception as e:
                    print(f"  {pattern_type:15s}: ERROR - {e}")
                    lang_results[pattern_type] = {'avg_time_ms': float('inf'), 'matches': 0}
            elif isinstance(pattern, list):
                # Handle lists like disclaimers/signatures
                for i, p in enumerate(pattern):
                    try:
                        avg_time, matches = benchmark_pattern(p, emails)
                        key = f"{pattern_type}_{i}"
                        lang_results[key] = {'avg_time_ms': avg_time * 1000, 'matches': matches}
                        print(f"  {key:15s}: {avg_time*1000:8.3f}ms avg, {matches:3d} matches")
                    except Exception as e:
                        print(f"  {key:15s}: ERROR - {e}")
        
        results[lang] = lang_results
    
    return results

def identify_bottlenecks(results: Dict) -> List[str]:
    """Identify the slowest patterns."""
    bottlenecks = []
    threshold_ms = 10.0  # Consider anything > 10ms as potentially slow
    
    def collect_slow_patterns(data, prefix=""):
        for key, value in data.items():
            if isinstance(value, dict):
                if 'avg_time_ms' in value and value['avg_time_ms'] > threshold_ms:
                    bottlenecks.append((f"{prefix}{key}", value['avg_time_ms']))
                else:
                    collect_slow_patterns(value, f"{prefix}{key}.")
    
    collect_slow_patterns(results)
    return sorted(bottlenecks, key=lambda x: x[1], reverse=True)

if __name__ == "__main__":
    print("=== Regex Performance Benchmark ===")
    results = benchmark_all_patterns()
    
    print(f"\n=== Performance Bottlenecks ===")
    bottlenecks = identify_bottlenecks(results)
    
    if bottlenecks:
        print("Slowest patterns (> 10ms):")
        for pattern_name, time_ms in bottlenecks[:10]:
            print(f"  {pattern_name:30s}: {time_ms:8.3f}ms")
    else:
        print("No significant bottlenecks found (all patterns < 10ms)")
    
    print(f"\nBenchmark complete. Results can be used for optimization priorities.")