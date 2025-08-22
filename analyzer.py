import os
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from prettytable import PrettyTable
from rich.console import Console
from rich.panel import Panel
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colorama import Fore, Style

console = Console()

# -----------------------------
# Detect installed browsers
# -----------------------------
def detect_browsers():
    paths = {
        "Edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "Chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "Firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe"
    }
    found = []
    for name, path in paths.items():
        if os.path.exists(path):
            found.append((name, path))
    return found

# -----------------------------
# Start browser driver
# -----------------------------
def start_driver(browser_name, browser_path):
    if browser_name == "Edge":
        options = EdgeOptions()
        options.binary_location = browser_path
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        service = EdgeService(executable_path=r"C:\Users\Fbouy\Downloads\edgedriver_win64\msedgedriver.exe")
        return webdriver.Edge(service=service, options=options)

    elif browser_name == "Chrome":
        options = ChromeOptions()
        options.binary_location = browser_path
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        service = ChromeService(executable_path=r"C:\Users\Fbouy\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe")
        return webdriver.Chrome(service=service, options=options)

    elif browser_name == "Firefox":
        options = FirefoxOptions()
        options.binary_location = browser_path
        options.add_argument("--headless")
        service = FirefoxService(executable_path=r"C:\Users\Fbouy\Downloads\geckodriver-v0.36.0-win32\geckodriver.exe")
        return webdriver.Firefox(service=service, options=options)

# -----------------------------
# Fake extension check
# -----------------------------
def check_extensions():
    return [
        ("AdBlock", "Read/Write Data"),
        ("Grammarly", "Full Access")
    ]

# -----------------------------
# Fake security settings
# -----------------------------
def check_security_settings():
    return {
        "Do Not Track": "Enabled",
        "Third-Party Cookies": "Blocked",
        "Password Manager": "Enabled",
        "HTTPS-Only Mode": "Enabled"
    }

# -----------------------------
# TLS/HTTPS check
# -----------------------------
def check_tls(driver, browser_name):
    browser_name = browser_name.lower()
    
    if browser_name in ["chrome", "edge"]:
        # Try multiple common tags for TLS info
        for tag in ["pre", "code", "div"]:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, tag))
                )
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        print(f" TLS info not found for {browser_name}. Returning empty JSON.")
        return "{}"
    
    elif browser_name == "firefox":
        return '{"error": "TLS inspection not supported via Selenium for Firefox"}'
    
    else:
        print(f" Unsupported browser: {browser_name}. Returning empty JSON.")
        return "{}"

# -----------------------------
# Calculate basic score
# -----------------------------
def calculate_risk(settings, extensions):
    score = 100
    if settings.get("Do Not Track") != "Enabled":
        score -= 10
    if settings.get("Third-Party Cookies") != "Blocked":
        score -= 20
    if len(extensions) > 5:
        score -= 5
    return score

# -----------------------------
# Save report
# -----------------------------
def save_reports(browser_name, extensions, settings, tls_info, score):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_data = {
        "browser": browser_name,
        "extensions": extensions,
        "settings": settings,
        "tls_info": tls_info[:300] + "...",
        "score": score
    }
    os.makedirs("reports", exist_ok=True)
    json_path = f"reports/{browser_name}_report_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=4)
    console.print(f"[green]Report saved:[/green] {json_path}")

# -----------------------------
# Main
# -----------------------------
def main():
    # Custom ASCII banner
    banner = f"""
{Fore.CYAN}
███╗   ███╗██╗   ██╗███████╗██████╗ ███████╗██████╗ 
████╗ ████║██║   ██║██╔════╝██╔══██╗██╔════╝██╔══██╗
██╔████╔██║██║   ██║█████╗  ██████╔╝█████╗  ██████╔╝
██║╚██╔╝██║██║   ██║██╔══╝  ██╔═══╝ ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║╚██████╔╝███████╗██║     ███████╗██║  ██║
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝
Multi-Browser Security Analyzer
{Style.RESET_ALL}
"""
    console.print(banner)

    browsers = detect_browsers()
    if not browsers:
        console.print("[red]No supported browsers detected![/red]")
        return

    for browser_name, browser_path in browsers:
        console.print(Panel.fit(f"Scanning {browser_name}", style="bold green"))
        driver = start_driver(browser_name, browser_path)

        extensions = check_extensions()
        settings = check_security_settings()
        tls_info = check_tls(driver, browser_name)
        score = calculate_risk(settings, extensions)

        # Display results
        console.print("\n[bold yellow]Installed Extensions:[/bold yellow]")
        table_ext = PrettyTable(["Extension Name", "Permissions"])
        for name, perm in extensions:
            table_ext.add_row([name, perm])
        print(table_ext)

        console.print("\n[bold yellow]Security/Privacy Settings:[/bold yellow]")
        table_set = PrettyTable(["Setting", "Status"])
        for key, val in settings.items():
            table_set.add_row([key, val])
        print(table_set)

        console.print("\n[bold yellow]TLS Info (truncated):[/bold yellow]")
        console.print(tls_info[:300] + "...")

        console.print(f"\n[cyan]Security Score for {browser_name}:[/cyan] [bold green]{score}/100[/bold green]")

        save_reports(browser_name, extensions, settings, tls_info, score)

        driver.quit()

    console.print(Panel.fit("Scan Complete!", style="bold cyan"))

if __name__ == "__main__":
    main()
