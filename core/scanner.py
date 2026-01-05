"""
Malware Scanner - Core scanning functionality
Integrates ML model for malware detection
Supports both PyTorch (.pth) and ONNX (.onnx) models
"""
import os
import numpy as np
from PIL import Image
from datetime import datetime
from pathlib import Path
import psutil

from utils.file_converter import FileConverter

# ========================================
# ONNX Runtime Import
# ========================================
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print(" ONNX Runtime not available. Install with: pip install onnxruntime")

# ========================================
# PyTorch Import (Conditional)
# ========================================
try:
    import torch
    from torch import nn
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
    
    #  PyTorch Model Class (only defined if torch available)
    class MalwareImageClassifier(nn.Module):
        """ResNet-18 based malware classifier (PyTorch)"""
        def __init__(self):
            super().__init__()
            self.model = models.resnet18()
            self.model.fc = nn.Linear(self.model.fc.in_features, 2)

        def forward(self, x):
            return self.model(x)
            
except ImportError:
    TORCH_AVAILABLE = False
    MalwareImageClassifier = None  # Dummy placeholder
    print("⚠️  PyTorch not available. Install with: pip install torch torchvision")

# ========================================
# Constants
# ========================================
DEFAULT_MODEL_PATH = "models/Modelv3.onnx"  # ONNX model by default
CLASS_NAMES = ["Benign", "Malware"]

# ========================================
# Malware Scanner
# ========================================
class MalwareScanner:
    def __init__(self, model_path=None):
        """
        Initialize Malware Scanner
        
        Args:
            model_path: Path to model file (.onnx or .pth)
                       If None, uses default ONNX model
        """
        # Use provided path or default path
        if model_path is None:
            script_dir = Path(__file__).resolve().parent.parent
            model_path = script_dir / DEFAULT_MODEL_PATH
        
        self.model_path = str(model_path)
        self.model = None
        self.session = None  # ONNX session
        self.device = None
        self.converter = FileConverter()
        self.is_onnx = self.model_path.endswith('.onnx')

        # Setup transforms based on model type
        if TORCH_AVAILABLE:
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Lambda(
                    lambda x: x.expand(3, -1, -1) if x.shape[0] == 1 else x
                ),
            ])
        else:
            self.transform = None

    def load_model(self):
        """Load model (ONNX or PyTorch)"""
        if self.model is not None or self.session is not None:
            return  # Model already loaded

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}\n"
                f"Please ensure the model file exists at the specified path."
            )

        if self.is_onnx:
            # ========================================
            # Load ONNX Model
            # ========================================
            if not ONNX_AVAILABLE:
                raise RuntimeError(
                    "ONNX Runtime not available. Install with: pip install onnxruntime"
                )

            # Create ONNX Runtime session
            providers = ['CPUExecutionProvider']
            if ort.get_available_providers().__contains__('CUDAExecutionProvider'):
                providers.insert(0, 'CUDAExecutionProvider')

            # ========================================
            # PENGATURAN CPU - UBAH DI SINI UNTUK MENGURANGI CPU USAGE!
            # ========================================
            # Batasi jumlah thread yang digunakan ONNX Runtime
            # Nilai default: semua core CPU (bisa 100% CPU usage)
            # Nilai yang disarankan:
            #   - 1 thread = CPU usage rendah (~10-20%), scan lambat
            #   - 2 thread = Balanced (~20-40%), scan sedang (REKOMENDASI)
            #   - 4 thread = CPU usage tinggi (~50-80%), scan cepat
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = psutil.cpu_count(logical=True)  # UBAH ANGKA INI (1-4) ini
            sess_options.inter_op_num_threads = 1  # UBAH ANGKA INI (1-4)
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  # Sequential lebih hemat CPU
            
            # Tambahan optimasi
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC

            self.session = ort.InferenceSession(
                self.model_path, 
                providers=providers,
                sess_options=sess_options
            )
            self.device = "CUDA" if providers[0] == 'CUDAExecutionProvider' else "CPU"

        else:
            # ========================================
            # Load PyTorch Model
            # ========================================
            if not TORCH_AVAILABLE:
                raise RuntimeError(
                    "PyTorch not available. Install with: pip install torch torchvision"
                )

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = MalwareImageClassifier().to(self.device)
            self.model.load_state_dict(
                torch.load(self.model_path, map_location=self.device, weights_only=True)
            )
            self.model.eval()

    def scan_file(self, file_path: str) -> dict:
        """
        Scan a file for malware

        Args:
            file_path: Path to the file to scan

        Returns:
            dict: Scan results containing label, confidence, and metadata
        """
        # Load model if not already loaded
        self.load_model()

        # Check if file is already an image
        file_path_obj = Path(file_path)
        is_image = file_path_obj.suffix.lower() in ['.png', '.jpg', '.jpeg']

        if is_image:
            # Use the image directly
            image_path = file_path
            file_size = os.path.getsize(file_path)
        else:
            # Convert file to image
            conversion_result = self.converter.convert_file_to_image(file_path)
            image_path = conversion_result['output_image']
            file_size = os.path.getsize(file_path)

        # Open and preprocess the image
        image = Image.open(image_path).convert("L")  # Convert to grayscale

        # Predict based on model type
        if self.is_onnx:
            output, predicted = self._predict_onnx(image)
        else:
            output, predicted = self._predict_pytorch(image)

        label = CLASS_NAMES[predicted]

        # Clean up converted image if it was created
        if not is_image and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass  # Ignore cleanup errors

        # Get device information
        device_name = self._get_device_name()
        device_count = self._get_device_count()
        
        # Generate file hash for deduplication
        import hashlib
        file_hash = self._generate_file_hash(file_path)

        # Prepare result
        result = {
            "result": label,
            "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "model": {
                "model": Path(self.model_path).name,
                "predicted_value": predicted,
                "predicted_output": output,
            },
            "device": {
                "device": str(self.device),
                "device_name": device_name,
                "device_count": device_count,
            },
            "file": {
                "file_name": file_path_obj.name,
                "file_size": file_size,
                "file_hash": file_hash,
            },
        }
        
        # Save to local queue for syncing to backend
        try:
            from .local_queue import LocalQueue
            queue = LocalQueue()
            queue.add_scan_result(
                filename=file_path_obj.name,
                label=label,
                file_hash=file_hash
            )
        except Exception as e:
            # Don't fail scan if queue save fails
            print(f"Warning: Failed to save to local queue: {e}")

        return result
    
    def _generate_file_hash(self, file_path: str) -> str:
        """
        Generate SHA256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash string
        """
        import hashlib
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            # Fallback to filename hash if file can't be read
            return hashlib.sha256(file_path.encode()).hexdigest()


    def _predict_onnx(self, image):
        """Run ONNX inference"""
        # Preprocess image for ONNX
        image_resized = image.resize((224, 224))
        image_array = np.array(image_resized).astype(np.float32) / 255.0

        # Expand to 3 channels if grayscale
        if len(image_array.shape) == 2:
            image_array = np.stack([image_array] * 3, axis=0)
        else:
            image_array = np.transpose(image_array, (2, 0, 1))

        # Add batch dimension
        image_array = np.expand_dims(image_array, axis=0)

        # Run inference
        input_name = self.session.get_inputs()[0].name
        output_name = self.session.get_outputs()[0].name
        result = self.session.run([output_name], {input_name: image_array})

        # Process output
        output = result[0][0]  # Get probabilities
        predicted = int(np.argmax(output))

        return output.tolist(), predicted

    def _predict_pytorch(self, image):
        """Run PyTorch inference"""
        image_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(image_tensor)
            predicted = torch.argmax(output, dim=1).item()

        return output.tolist()[0], predicted

    def _get_device_name(self):
        """Get device name"""
        if self.is_onnx:
            return "CUDA" if self.device == "CUDA" else "CPU"
        else:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
            return "CPU"

    def _get_device_count(self):
        """Get device count"""
        if self.is_onnx:
            return 1
        else:
            if TORCH_AVAILABLE and torch.cuda.is_available():
                return torch.cuda.device_count()
            return 1
