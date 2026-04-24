#!/usr/bin/env python3
"""
Start the Music Transfer Web UI
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import app
from colorama import init, Fore, Style

init(autoreset=True)

if __name__ == '__main__':
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  🎵 Universal Music Transfer - Web UI{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.GREEN}  เปิดเว็บที่:{Style.RESET_ALL} http://localhost:5000")
    print(f"{Fore.YELLOW}  กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์{Style.RESET_ALL}\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
