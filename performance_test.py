"""
Performance Testing Script
Menguji performa scanning dengan berbagai konfigurasi thread dan delay
Menghasilkan tabel hasil pengujian
"""
import os
import sys
import time
import psutil
import threading
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

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
                # Get CPU percentage (per-process)
                cpu_percent = self.process.cpu_percent(interval=0.1)
                self.cpu_samples.append(cpu_percent)
                
                # Get RAM usage in MB
                ram_mb = self.process.memory_info().rss / 1024 / 1024
                self.ram_samples.append(ram_mb)
                
                time.sleep(0.1)  # Sample every 100ms
            except:
                pass
                
    def get_stats(self):
        """Get statistics dari monitoring"""
        if not self.cpu_samples or not self.ram_samples:
            return {
                'min_cpu': 0,
                'max_cpu': 0,
                'avg_cpu': 0,
                'min_ram': 0,
                'max_ram': 0,
                'avg_ram': 0
            }
            
        return {
            'min_cpu': min(self.cpu_samples),
            'max_cpu': max(self.cpu_samples),
            'avg_cpu': sum(self.cpu_samples) / len(self.cpu_samples),
            'min_ram': min(self.ram_samples),
            'max_ram': max(self.ram_samples),
            'avg_ram': sum(self.ram_samples) / len(self.ram_samples)
        }


class PerformanceTest:
    """Class untuk menjalankan performance testing"""
    
    def __init__(self):
        self.scanner = MalwareScanner()
        self.results = []
        
    def test_configuration(self, num_threads, delay_ms, test_file):
        """
        Test satu konfigurasi
        
        Args:
            num_threads: Jumlah thread ONNX
            delay_ms: Delay antar file (ms)
            test_file: File untuk di-scan
        """
        print(f"\n{'='*60}")
        print(f"Testing: Threads={num_threads}, Delay={delay_ms}ms")
        print(f"File: {test_file}")
        print(f"{'='*60}")
        
        # Update scanner configuration
        import onnxruntime as ort
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = num_threads
        sess_options.inter_op_num_threads = num_threads
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        
        # Reload scanner dengan konfigurasi baru
        self.scanner.session = None
        self.scanner.model = None
        
        # Create new session with updated options
        providers = ['CPUExecutionProvider']
        self.scanner.session = ort.InferenceSession(
            self.scanner.model_path,
            providers=providers,
            sess_options=sess_options
        )
        
        # Start performance monitoring
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Run scan
        start_time = time.time()
        
        try:
            result = self.scanner.scan_file(test_file)
            scan_success = True
        except Exception as e:
            print(f"❌ Error during scan: {e}")
            scan_success = False
            result = None
        
        end_time = time.time()
        
        # Stop monitoring
        time.sleep(0.5)  # Let monitoring catch up
        monitor.stop()
        
        # Get stats
        stats = monitor.get_stats()
        scan_time = end_time - start_time
        
        # Store result
        test_result = {
            'threads': num_threads,
            'delay': delay_ms,
            'file': Path(test_file).name,
            'time': f"{scan_time:.2f}s",
            'ram_avg': f"{stats['avg_ram']:.1f} MB",
            'ram_max': f"{stats['max_ram']:.1f} MB",
            'cpu_min': f"{stats['min_cpu']:.1f}%",
            'cpu_max': f"{stats['max_cpu']:.1f}%",
            'cpu_avg': f"{stats['avg_cpu']:.1f}%",
            'success': '✓' if scan_success else '✗',
            'result': result.get('result', 'N/A') if result else 'N/A'
        }
        
        self.results.append(test_result)
        
        print(f"\n📊 Results:")
        print(f"  Time: {scan_time:.2f}s")
        print(f"  RAM: {stats['avg_ram']:.1f} MB (max: {stats['max_ram']:.1f} MB)")
        print(f"  CPU: {stats['avg_cpu']:.1f}% (min: {stats['min_cpu']:.1f}%, max: {stats['max_cpu']:.1f}%)")
        print(f"  Detection: {result.get('result', 'N/A') if result else 'N/A'}")
        
        return test_result
        
    def run_tests(self, test_files, thread_configs, delay_configs):
        """
        Run semua kombinasi test
        
        Args:
            test_files: List file untuk di-test
            thread_configs: List jumlah thread untuk di-test
            delay_configs: List delay untuk di-test
        """
        print("\n" + "="*60)
        print("🚀 PERFORMANCE TESTING - MALWARE SCANNER")
        print("="*60)
        print(f"Test Files: {len(test_files)}")
        print(f"Thread Configs: {thread_configs}")
        print(f"Delay Configs: {delay_configs}")
        print(f"Total Tests: {len(test_files) * len(thread_configs) * len(delay_configs)}")
        print("="*60)
        
        self.results = []
        
        for test_file in test_files:
            if not os.path.exists(test_file):
                print(f"⚠️  File not found: {test_file}")
                continue
                
            for num_threads in thread_configs:
                for delay_ms in delay_configs:
                    self.test_configuration(num_threads, delay_ms, test_file)
                    time.sleep(1)  # Cooldown between tests
                    
    def print_results_table(self):
        """Print hasil dalam bentuk tabel"""
        if not self.results:
            print("\n⚠️  No results to display")
            return
            
        print("\n" + "="*80)
        print("📊 PERFORMANCE TEST RESULTS")
        print("="*80)
        
        # Prepare table data
        headers = [
            "Thread",
            "Delay",
            "File",
            "Time",
            "RAM Avg",
            "RAM Max",
            "CPU Min",
            "CPU Max",
            "CPU Avg",
            "Status",
            "Result"
        ]
        
        table_data = []
        for r in self.results:
            table_data.append([
                r['threads'],
                f"{r['delay']}ms",
                r['file'][:20],  # Truncate long filenames
                r['time'],
                r['ram_avg'],
                r['ram_max'],
                r['cpu_min'],
                r['cpu_max'],
                r['cpu_avg'],
                r['success'],
                r['result']
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
    def save_results_csv(self, output_file="performance_results.csv"):
        """Save hasil ke CSV file"""
        if not self.results:
            print("\n⚠️  No results to save")
            return
            
        import csv
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
            writer.writeheader()
            writer.writerows(self.results)
            
        print(f"\n💾 Results saved to: {output_file}")


def main():
    """Main function"""
    # ========================================
    # KONFIGURASI TEST
    # ========================================
    
    # File untuk di-test (ganti dengan file Anda)
    test_files = [
        r"C:\Users\saefu\Documents\Mango-app-almost\desktop_app\test_samples\malware_sample.exe",
        r"C:\Users\saefu\Documents\Mango-app-almost\desktop_app\test_samples\benign_sample.txt",
    ]
    
    # Konfigurasi thread yang akan di-test
    thread_configs = [1, 2, 4, 8]
    
    # Konfigurasi delay yang akan di-test (ms)
    delay_configs = [0, 50, 100, 200]
    
    # ========================================
    # RUN TESTS
    # ========================================
    
    tester = PerformanceTest()
    tester.run_tests(test_files, thread_configs, delay_configs)
    
    # ========================================
    # DISPLAY RESULTS
    # ========================================
    
    tester.print_results_table()
    
    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"performance_results_{timestamp}.csv"
    tester.save_results_csv(csv_filename)
    
    print("\n✅ Performance testing completed!")


if __name__ == "__main__":
    # Check dependencies
    try:
        import tabulate
    except ImportError:
        print("❌ Missing dependency: tabulate")
        print("Install with: pip install tabulate")
        sys.exit(1)
        
    try:
        import psutil
    except ImportError:
        print("❌ Missing dependency: psutil")
        print("Install with: pip install psutil")
        sys.exit(1)
    
    main()
