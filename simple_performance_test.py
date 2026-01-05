"""
Simple Performance Testing Script
Menguji performa scanning dengan berbagai konfigurasi
"""
import os
import sys
import time
import psutil
import threading
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.scanner import MalwareScanner


class PerformanceMonitor:
    """Monitor CPU dan RAM usage"""
    
    def __init__(self):
        self.cpu_samples = []
        self.ram_samples = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.process = psutil.Process()
        
    def start(self):
        self.is_monitoring = True
        self.cpu_samples = []
        self.ram_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop(self):
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            
    def _monitor_loop(self):
        while self.is_monitoring:
            try:
                cpu_percent = self.process.cpu_percent(interval=0.1)
                self.cpu_samples.append(cpu_percent)
                
                ram_mb = self.process.memory_info().rss / 1024 / 1024
                self.ram_samples.append(ram_mb)
                
                time.sleep(0.1)
            except:
                pass
                
    def get_stats(self):
        if not self.cpu_samples or not self.ram_samples:
            return {'min_cpu': 0, 'max_cpu': 0, 'avg_ram': 0}
            
        return {
            'min_cpu': min(self.cpu_samples),
            'max_cpu': max(self.cpu_samples),
            'avg_ram': sum(self.ram_samples) / len(self.ram_samples)
        }


def test_scan(test_file, num_threads=2):
    """Test single scan"""
    print(f"\nTesting: {Path(test_file).name}")
    print(f"Threads: {num_threads}")
    
    # Create scanner
    scanner = MalwareScanner()
    
    # Update ONNX configuration
    try:
        import onnxruntime as ort
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = num_threads
        sess_options.inter_op_num_threads = num_threads
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        providers = ['CPUExecutionProvider']
        scanner.session = ort.InferenceSession(
            scanner.model_path,
            providers=providers,
            sess_options=sess_options
        )
    except Exception as e:
        print(f"Warning: Could not configure ONNX: {e}")
    
    # Start monitoring
    monitor = PerformanceMonitor()
    monitor.start()
    
    # Run scan
    start_time = time.time()
    try:
        result = scanner.scan_file(test_file)
        success = True
    except Exception as e:
        print(f"Error: {e}")
        success = False
        result = None
    
    end_time = time.time()
    
    # Stop monitoring
    time.sleep(0.5)
    monitor.stop()
    
    # Get stats
    stats = monitor.get_stats()
    scan_time = end_time - start_time
    
    return {
        'threads': num_threads,
        'file': Path(test_file).name,
        'time': scan_time,
        'ram': stats['avg_ram'],
        'cpu_min': stats['min_cpu'],
        'cpu_max': stats['max_cpu'],
        'success': success,
        'result': result.get('result', 'N/A') if result else 'N/A'
    }


def print_table(results):
    """Print hasil dalam bentuk tabel"""
    print("\n" + "="*100)
    print("PERFORMANCE TEST RESULTS")
    print("="*100)
    
    # Header
    print(f"{'Thread':<8} {'Delay':<8} {'File':<25} {'Time':<10} {'RAM Usage':<15} {'Min CPU':<12} {'Max CPU':<12}")
    print("-"*100)
    
    # Data
    for r in results:
        print(f"{r['threads']:<8} {r.get('delay', 0):<8} {r['file']:<25} {r['time']:.2f}s{'':<5} {r['ram']:.1f} MB{'':<6} {r['cpu_min']:.1f}%{'':<6} {r['cpu_max']:.1f}%")
    
    print("="*100)


def main():
    """Main function"""
    print("\n🚀 PERFORMANCE TESTING - MALWARE SCANNER")
    print("="*60)
    
    # Test file - gunakan file yang ada
    test_file = r"test_samples\benign_sample.txt"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("Creating test file...")
        os.makedirs("test_samples", exist_ok=True)
        with open(test_file, 'w') as f:
            f.write("This is a test file for performance testing.")
    
    # Run tests dengan berbagai konfigurasi thread
    results = []
    
    thread_configs = [1, 2, 4, 8]
    
    for num_threads in thread_configs:
        result = test_scan(test_file, num_threads)
        result['delay'] = 0  # Add delay column (default 0)
        results.append(result)
        time.sleep(1)  # Cooldown
    
    # Print results
    print_table(results)
    
    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"performance_results_{timestamp}.csv"
    
    with open(csv_file, 'w') as f:
        f.write("Thread,Delay,File,Time,Ram Usage,Minimum CPU usage,Max Cpu Usage\n")
        for r in results:
            f.write(f"{r['threads']},{r.get('delay', 0)},{r['file']},{r['time']:.2f}s,{r['ram']:.1f} MB,{r['cpu_min']:.1f}%,{r['cpu_max']:.1f}%\n")
    
    print(f"\n💾 Results saved to: {csv_file}")
    print("✅ Testing completed!")


if __name__ == "__main__":
    # Check dependencies
    try:
        import psutil
    except ImportError:
        print("❌ Missing dependency: psutil")
        print("Install with: pip install psutil")
        sys.exit(1)
    
    main()
