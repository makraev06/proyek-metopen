from urllib.parse import urlparse, urlunparse
import ipaddress


FEATURE_COLUMNS = [
    "URLLength",
    "DomainLength",
    "IsDomainIP",
    "TLDLength",
    "NoOfSubDomain",
    "NoOfLettersInURL",
    "LetterRatioInURL",
    "NoOfDegitsInURL",
    "DegitRatioInURL",
    "NoOfEqualsInURL",
    "NoOfQMarkInURL",
    "NoOfAmpersandInURL",
    "NoOfOtherSpecialCharsInURL",
    "SpacialCharRatioInURL",
    "IsHTTPS"
]

def normalize_url(url):
    url = str(url).strip()

    if "://" not in url:
        url = "http://" + url

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path

    if path == "/":
        path = ""

    return urlunparse((
        scheme,
        netloc,
        path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))

    parsed = urlparse(url)
def extract_features(url):
    raw_url = normalize_url(url)

    parsed = urlparse(raw_url)
    domain = parsed.hostname or ""

    url_length = len(raw_url)
    domain_length = len(domain)

    try:
        ipaddress.ip_address(domain)
        is_domain_ip = 1
    except ValueError:
        is_domain_ip = 0

    domain_parts = domain.split(".")
    tld = domain_parts[-1] if len(domain_parts) > 1 else ""

    tld_length = len(tld)
    no_of_subdomain = max(len(domain_parts) - 2, 0)

    no_of_letters = sum(
        c.isalpha()
        for c in raw_url
    )

    letter_ratio = (
        no_of_letters / url_length
        if url_length > 0 else 0
    )

    no_of_digits = sum(
        c.isdigit()
        for c in raw_url
    )

    digit_ratio = (
        no_of_digits / url_length
        if url_length > 0 else 0
    )

    no_of_equals = raw_url.count("=")
    no_of_qmark = raw_url.count("?")
    no_of_ampersand = raw_url.count("&")

    no_of_special_chars = sum(
        1 for c in raw_url
        if not c.isalnum()
    )

    special_char_ratio = (
        no_of_special_chars / url_length
        if url_length > 0 else 0
    )

    is_https = (
        1
        if parsed.scheme.lower() == "https"
        else 0
    )

    return {
        "URLLength": url_length,
        "DomainLength": domain_length,
        "IsDomainIP": is_domain_ip,
        "TLDLength": tld_length,
        "NoOfSubDomain": no_of_subdomain,
        "NoOfLettersInURL": no_of_letters,
        "LetterRatioInURL": letter_ratio,
        "NoOfDegitsInURL": no_of_digits,
        "DegitRatioInURL": digit_ratio,
        "NoOfEqualsInURL": no_of_equals,
        "NoOfQMarkInURL": no_of_qmark,
        "NoOfAmpersandInURL": no_of_ampersand,
        "NoOfOtherSpecialCharsInURL": no_of_special_chars,
        "SpacialCharRatioInURL": special_char_ratio,
        "IsHTTPS": is_https
    }
    
def get_hostname(url):
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    return (parsed.hostname or "").lower()
