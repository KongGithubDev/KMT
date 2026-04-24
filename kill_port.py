#!/usr/bin/env python3
"""
Kill process by port number
"""
import sys
import subprocess
import os

def kill_port(port):
    """Kill process listening on specified port"""
    try:
        # Find PID using the port
        result = subprocess.run(
            ['netstat', '-ano', '|', 'findstr', f':{port}'],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode != 0 or not result.stdout:
            print(f"❌ ไม่พบ process ที่ใช้ port {port}")
            return False
        
        # Parse output to find PID
        lines = result.stdout.strip().split('\n')
        pids = set()
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(int(pid))
        
        if not pids:
            print(f"❌ ไม่พบ PID สำหรับ port {port}")
            return False
        
        # Kill each PID
        for pid in pids:
            try:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
                print(f"✅ ปิด PID {pid} สำเร็จ")
            except subprocess.CalledProcessError as e:
                print(f"❌ ไม่สามารถปิด PID {pid}: {e}")
        
        print(f"\n✅ Port {port} ว่างแล้ว")
        return True
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("ใช้: python kill_port.py <port>")
        print("ตัวอย่าง: python kill_port.py 5000")
        sys.exit(1)
    
    port = sys.argv[1]
    if not port.isdigit():
        print("❌ Port ต้องเป็นตัวเลข")
        sys.exit(1)
    
    kill_port(int(port))
