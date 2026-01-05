"""
Full Scan Performance Test Script
Menguji performa scanning dengan simulasi batch processing
Menghasilkan tabel sesuai format yang diminta user:
Thread | Delay | File | Time | Ram Usage | Minimum CPU usage | Max Cpu Usage
"""
import os
import sys
import time
import psutil
import threading
from pathlib import Path
from datetime import datetime
from tabulate import tabulate
from unittest.mock import MagicMock

# ==========================================
# MOCK DATABASE TO AVOID LOCKING ISSUES
# ==========================================
# We want to measure SCAN performance, not DB write performance
mock_queue = MagicMock()
sys.modules['core.local_queue'] = mock_queue

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.scanner import MalwareScanner

class PerformanceMonitor:
    """Monitor CPU dan RAM usage selama scanning"""
    
    def __init__(self):
        self.cpu_samples = []
        self.ram_samples = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()
        
    def start(self):
        """Mulai monitoring"""
        self.is_monitoring = True
        self.cpu_samples = []
        self.ram_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            
    def _monitor_loop(self):
        """Loop untuk monitoring resources"""
        while self.is_monitoring:
            try:
                # Use faster interval for more resolution
                cpu_percent = self.process.cpu_percent(interval=0.05)
                self.cpu_samples.append(cpu_percent)
                
                ram_mb = self.process.memory_info().rss / 1024 / 1024
                self.ram_samples.append(ram_mb)
            except:
                pass
                
    def get_stats(self):
        """Get statistics dari monitoring"""
        if not self.cpu_samples or not self.ram_samples:
            return {
                'min_cpu': 0, 'max_cpu': 0, 'avg_cpu': 0,
                'min_ram': 0, 'max_ram': 0, 'avg_ram': 0
            }
            
        return {
            'min_cpu': min(self.cpu_samples),
            'max_cpu': max(self.cpu_samples),
            'avg_cpu': sum(self.cpu_samples) / len(self.cpu_samples),
            'min_ram': min(self.ram_samples),
            'max_ram': max(self.ram_samples),
            'avg_ram': sum(self.ram_samples) / len(self.ram_samples)
        }

class FullScanTester:
    def __init__(self):
        # Suppress prints from scanner if any
        self.scanner = MalwareScanner()
        self.results = []
        
        # Sample file to scan repeatedly
        self.sample_file = r"C:\Users\saefu\Documents\Mango-app-almost\desktop_app\test_samples\malware_sample.exe"
        if not os.path.exists(self.sample_file):
            os.makedirs(os.path.dirname(self.sample_file), exist_ok=True)
            with open(self.sample_file, 'wb') as f:
                f.write(b'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*')

    def run_benchmark(self, num_threads, delay_ms, file_count):
        """
        Jalankan benchmark untuk konfigurasi tertentu
        """
        print(f"\n🚀 Running Benchmark: Threads={num_threads}, Delay={delay_ms}ms, Files={file_count}")
        
        # 1. Configure ONNX Runtime Threads
        import onnxruntime as ort
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = num_threads
        sess_options.inter_op_num_threads = num_threads
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        
        # Reload scanner with new config
        self.scanner.session = None
        providers = ['CPUExecutionProvider']
        self.scanner.session = ort.InferenceSession(
            self.scanner.model_path,
            providers=providers,
            sess_options=sess_options
        )
        
        # 2. Start Monitoring
        monitor = PerformanceMonitor()
        monitor.start()
        start_time = time.time()
        
        # 3. Simulated Full Scan Loop
        print("   Progress: ", end="", flush=True)
        for i in range(file_count):
            try:
                self.scanner.scan_file(self.sample_file)
                
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)
                    
                if (i + 1) % (file_count // 10 if file_count >= 10 else 1) == 0:
                    print(".", end="", flush=True)
                    
            except Exception as e:
                print(f"x", end="", flush=True)
        print(" Done!")
        
        end_time = time.time()
        monitor.stop()
        
        # 4. Calculate Stats
        total_time = end_time - start_time
        stats = monitor.get_stats()
        
        if total_time > 60:
            time_str = f"{total_time/60:.1f} Menit"
        else:
            time_str = f"{total_time:.1f} Detik"

        # 5. Store Result
        result_entry = [
            num_threads,
            "No" if delay_ms == 0 else f"{delay_ms}ms",
            file_count,
            time_str,
            f"{stats['avg_ram']:.1f}mb",     # Ram Usage (Avg)
            f"{stats['min_cpu']:.0f}%",      # Minimum CPU usage
            f"{stats['max_cpu']:.0f}%"       # Max Cpu Usage
        ]
        self.results.append(result_entry)
        
    def print_table(self):
        headers = ["Thread", "Delay", "File", "Time", "Ram Usage", "Minimum\nCPU usage", "Max Cpu Usage"]
        
        output = []
        output.append("\n" + "="*80)
        output.append("HASIL TESTING")
        output.append("="*80)
        output.append(tabulate(self.results, headers=headers, tablefmt="grid"))
        output.append("\n")
        
        # Print to console
        print("\n".join(output))
        
        # Save to file
        try:
            with open("results.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output))
            print("Results saved to results.txt")
        except Exception as e:
            print(f"Error saving results: {e}")

def main():
    tester = FullScanTester()
    
    # === KONFIGURASI BENCHMARK ===
    
    # Case 1: 8 Threads, No Delay, 1000 Files
    # Estimated time: ~50-80 seconds
    tester.run_benchmark(num_threads=8, delay_ms=0, file_count=1000)
    
    # Case 2: 4 Threads, 100ms Delay, 200 Files
    # Estimated time: ~20-30 seconds
    tester.run_benchmark(num_threads=4, delay_ms=100, file_count=200) 
    
    # Case 3: Unlimited Estimation (Based on Case 1 Speed)
    # Extrapolate to 100,000 files (typical system size)
    if len(tester.results) > 0:
        # Get data from first result (8 threads, 0 delay)
        r = tester.results[0]
        # Parse time string roughly to get seconds
        time_str = r[3] 
        if "Detik" in time_str:
            seconds = float(time_str.replace(" Detik", ""))
        elif "Menit" in time_str:
            seconds = float(time_str.replace(" Menit", "")) * 60
        else:
            seconds = 0
            
        files = r[2] # 1000
        avg_per_file = seconds / files if files > 0 else 0
        
        est_files = 100000
        est_seconds = avg_per_file * est_files
        est_hours = est_seconds / 3600
        
        tester.results.append([
            8,
            "No",
            "Unlimited\n(~100k files)",
            f"{est_hours:.1f} Jam",
            f"{r[4]} (Est)",
            f"{r[5]} (Est)",
            f"{r[6]} (Est)"
        ])

    tester.print_table()

if __name__ == "__main__":
    main()
