import os
import json
import sqlite3
import winreg
import platform
import subprocess
from datetime import datetime
from pathlib import Path
import requests
import ssl
import socket
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
import tempfile

console = Console()

class BrowserSecurityAnalyzer:
    def __init__(self):
        self.system = platform.system()
        self.results = {}
        
    def detect_browsers(self):
        """Detect installed browsers and their versions"""
        browsers = {}
        
        if self.system == "Windows":
            # Chrome
            try:
                chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                if os.path.exists(chrome_path):
                    result = subprocess.run([chrome_path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    version = result.stdout.strip().split()[-1] if result.stdout else "Unknown"
                    browsers["Chrome"] = {"path": chrome_path, "version": version}
            except:
                pass
                
            # Edge
            try:
                edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                if os.path.exists(edge_path):
                    result = subprocess.run([edge_path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    version = result.stdout.strip().split()[-1] if result.stdout else "Unknown"
                    browsers["Edge"] = {"path": edge_path, "version": version}
            except:
                pass
                
            # Firefox
            try:
                firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"
                if os.path.exists(firefox_path):
                    result = subprocess.run([firefox_path, "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    version = result.stdout.strip().split()[-1] if result.stdout else "Unknown"
                    browsers["Firefox"] = {"path": firefox_path, "version": version}
            except:
                pass
        
        return browsers
    
    def get_chrome_extensions(self):
        """Get real Chrome extensions from user data"""
        extensions = []
        if self.system == "Windows":
            chrome_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default")
            extensions_path = os.path.join(chrome_user_data, "Extensions")
            
            if os.path.exists(extensions_path):
                for ext_id in os.listdir(extensions_path):
                    ext_path = os.path.join(extensions_path, ext_id)
                    if os.path.isdir(ext_path):
                        # Look for manifest in version folders
                        for version_folder in os.listdir(ext_path):
                            manifest_path = os.path.join(ext_path, version_folder, "manifest.json")
                            if os.path.exists(manifest_path):
                                try:
                                    with open(manifest_path, 'r', encoding='utf-8') as f:
                                        manifest = json.load(f)
                                        name = manifest.get('name', ext_id)
                                        permissions = manifest.get('permissions', [])
                                        extensions.append({
                                            "id": ext_id,
                                            "name": name,
                                            "permissions": permissions,
                                            "version": version_folder
                                        })
                                        break
                                except:
                                    continue
        return extensions
    
    def get_firefox_extensions(self):
        """Get real Firefox extensions"""
        extensions = []
        if self.system == "Windows":
            firefox_profile_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
            
            if os.path.exists(firefox_profile_path):
                for profile_folder in os.listdir(firefox_profile_path):
                    if profile_folder.endswith('.default-release'):
                        addons_path = os.path.join(firefox_profile_path, profile_folder, "addons.json")
                        if os.path.exists(addons_path):
                            try:
                                with open(addons_path, 'r', encoding='utf-8') as f:
                                    addons_data = json.load(f)
                                    for addon in addons_data.get('addons', []):
                                        if addon.get('active', False):
                                            extensions.append({
                                                "id": addon.get('id', 'unknown'),
                                                "name": addon.get('defaultLocale', {}).get('name', 'Unknown'),
                                                "permissions": addon.get('userPermissions', {}).get('permissions', []),
                                                "version": addon.get('version', 'Unknown')
                                            })
                                break
                            except:
                                continue
        return extensions
    
    def get_chrome_security_settings(self):
        """Extract real Chrome security settings from preferences"""
        settings = {}
        if self.system == "Windows":
            prefs_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Preferences")
            
            if os.path.exists(prefs_path):
                try:
                    with open(prefs_path, 'r', encoding='utf-8') as f:
                        prefs = json.load(f)
                        
                    # Extract security-related settings
                    settings['safe_browsing'] = prefs.get('safebrowsing', {}).get('enabled', False)
                    settings['password_manager'] = prefs.get('credentials_enable_service', False)
                    settings['autofill_enabled'] = prefs.get('autofill', {}).get('enabled', False)
                    settings['dns_prefetching'] = prefs.get('dns_prefetching', {}).get('enabled', True)
                    settings['third_party_cookies'] = prefs.get('profile', {}).get('block_third_party_cookies', False)
                    settings['do_not_track'] = prefs.get('enable_do_not_track', False)
                    
                except:
                    settings['error'] = "Could not read Chrome preferences"
                    
        return settings
    
    def get_firefox_security_settings(self):
        """Extract real Firefox security settings from prefs.js"""
        settings = {}
        if self.system == "Windows":
            firefox_profile_path = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
            
            if os.path.exists(firefox_profile_path):
                for profile_folder in os.listdir(firefox_profile_path):
                    if profile_folder.endswith('.default-release'):
                        prefs_path = os.path.join(firefox_profile_path, profile_folder, "prefs.js")
                        if os.path.exists(prefs_path):
                            try:
                                with open(prefs_path, 'r', encoding='utf-8') as f:
                                    prefs_content = f.read()
                                
                                # Parse key security settings
                                settings['tracking_protection'] = 'privacy.trackingprotection.enabled", true' in prefs_content
                                settings['safe_browsing'] = 'browser.safebrowsing.malware.enabled", true' in prefs_content
                                settings['https_only'] = 'dom.security.https_only_mode", true' in prefs_content
                                settings['password_manager'] = 'signon.rememberSignons", true' in prefs_content
                                settings['do_not_track'] = 'privacy.donottrackheader.enabled", true' in prefs_content
                                
                                break
                            except:
                                settings['error'] = "Could not read Firefox preferences"
                                break
        
        return settings
    
    def check_certificate_store(self):
        """Check Windows certificate store for suspicious certificates"""
        suspicious_certs = []
        try:
            if self.system == "Windows":
                result = subprocess.run([
                    "powershell", "-Command",
                    "Get-ChildItem -Path Cert:\\CurrentUser\\Root | Select-Object Subject, Issuer, NotAfter"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[3:]:  # Skip headers
                        if line.strip() and any(suspicious in line.lower() for suspicious in 
                                              ['superfish', 'lenovo', 'komodia', 'privdog']):
                            suspicious_certs.append(line.strip())
        except:
            pass
            
        return suspicious_certs
    
    def test_tls_configuration(self, hostname="www.google.com"):
        """Test TLS configuration for a given hostname"""
        tls_info = {}
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    tls_info['protocol'] = ssock.version()
                    tls_info['cipher'] = ssock.cipher()
                    cert = ssock.getpeercert()
                    tls_info['certificate_subject'] = dict(x[0] for x in cert['subject'])
                    tls_info['certificate_issuer'] = dict(x[0] for x in cert['issuer'])
                    tls_info['certificate_version'] = cert['version']
                    tls_info['serial_number'] = cert['serialNumber']
        except Exception as e:
            tls_info['error'] = str(e)
            
        return tls_info
    
    def calculate_security_score(self, browser_data):
        """Calculate a real security score based on actual findings"""
        score = 100
        
        # Check extensions (high-risk extensions reduce score more)
        extensions = browser_data.get('extensions', [])
        high_risk_perms = ['tabs', 'history', 'cookies', '<all_urls>', 'webRequest']
        
        for ext in extensions:
            permissions = ext.get('permissions', [])
            risk_count = sum(1 for perm in permissions if any(risk in str(perm).lower() for risk in high_risk_perms))
            if risk_count > 2:
                score -= 15
            elif risk_count > 0:
                score -= 5
        
        # Check security settings
        settings = browser_data.get('security_settings', {})
        if not settings.get('safe_browsing', False):
            score -= 20
        if not settings.get('do_not_track', False):
            score -= 10
        if not settings.get('third_party_cookies', False):
            score -= 15
        
        # Check for suspicious certificates
        if browser_data.get('suspicious_certificates', []):
            score -= 25
            
        return max(0, score)
    
    def generate_report(self, browser_name, browser_data):
        """Generate a detailed security report"""
        report = {
            'browser': browser_name,
            'version': browser_data.get('version', 'Unknown'),
            'timestamp': datetime.now().isoformat(),
            'extensions': browser_data.get('extensions', []),
            'security_settings': browser_data.get('security_settings', {}),
            'tls_info': browser_data.get('tls_info', {}),
            'suspicious_certificates': browser_data.get('suspicious_certificates', []),
            'security_score': browser_data.get('security_score', 0),
            'recommendations': []
        }
        
        # Generate recommendations
        if report['security_score'] < 70:
            report['recommendations'].append("Enable safe browsing protection")
        if report['security_score'] < 80:
            report['recommendations'].append("Review installed extensions and their permissions")
        if browser_data.get('suspicious_certificates'):
            report['recommendations'].append("Remove suspicious certificates from certificate store")
        
        return report
    
    def run_analysis(self):
        """Run the complete browser security analysis"""
        console.print(Panel.fit("Real Browser Security Analyzer", style="bold cyan"))
        
        browsers = self.detect_browsers()
        if not browsers:
            console.print("[red]No browsers detected![/red]")
            return
        
        with Progress() as progress:
            task = progress.add_task("Analyzing browsers...", total=len(browsers))
            
            for browser_name, browser_info in browsers.items():
                console.print(f"\n[bold green]Analyzing {browser_name}[/bold green]")
                
                browser_data = {
                    'version': browser_info['version'],
                    'extensions': [],
                    'security_settings': {},
                    'tls_info': {},
                    'suspicious_certificates': []
                }
                
                # Get extensions
                if browser_name == "Chrome":
                    browser_data['extensions'] = self.get_chrome_extensions()
                    browser_data['security_settings'] = self.get_chrome_security_settings()
                elif browser_name == "Firefox":
                    browser_data['extensions'] = self.get_firefox_extensions()
                    browser_data['security_settings'] = self.get_firefox_security_settings()
                
                # Test TLS
                browser_data['tls_info'] = self.test_tls_configuration()
                
                # Check certificates (once for all browsers)
                if browser_name == list(browsers.keys())[0]:  # Only run once
                    browser_data['suspicious_certificates'] = self.check_certificate_store()
                
                # Calculate score
                browser_data['security_score'] = self.calculate_security_score(browser_data)
                
                # Display results
                self.display_results(browser_name, browser_data)
                
                # Generate and save report
                report = self.generate_report(browser_name, browser_data)
                self.save_report(report)
                
                progress.advance(task)
        
        console.print(Panel.fit("Analysis Complete!", style="bold green"))
    
    def display_results(self, browser_name, browser_data):
        """Display analysis results in a formatted table"""
        # Extensions table
        if browser_data['extensions']:
            ext_table = Table(title=f"{browser_name} Extensions")
            ext_table.add_column("Name", style="cyan")
            ext_table.add_column("Version", style="magenta")
            ext_table.add_column("High-Risk Permissions", style="red")
            
            high_risk_perms = ['tabs', 'history', 'cookies', '<all_urls>', 'webRequest']
            for ext in browser_data['extensions'][:10]:  # Limit display
                risky_perms = [p for p in ext.get('permissions', []) 
                             if any(risk in str(p).lower() for risk in high_risk_perms)]
                ext_table.add_row(
                    ext.get('name', 'Unknown')[:30],
                    ext.get('version', 'Unknown'),
                    ', '.join(risky_perms[:3])
                )
            console.print(ext_table)
        
        # Security settings
        settings_table = Table(title=f"{browser_name} Security Settings")
        settings_table.add_column("Setting", style="cyan")
        settings_table.add_column("Status", style="green")
        
        for setting, value in browser_data.get('security_settings', {}).items():
            status = "✓ Enabled" if value else "✗ Disabled"
            color = "green" if value else "red"
            settings_table.add_row(setting.replace('_', ' ').title(), f"[{color}]{status}[/{color}]")
        
        console.print(settings_table)
        
        # Security score
        score = browser_data.get('security_score', 0)
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        console.print(f"\n[bold]Security Score: [{score_color}]{score}/100[/{score_color}][/bold]")
    
    def save_report(self, report):
        """Save the analysis report to a JSON file"""
        os.makedirs("security_reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"security_reports/{report['browser']}_security_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        console.print(f"[green]Report saved: {filename}[/green]")

def main():
    analyzer = BrowserSecurityAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()