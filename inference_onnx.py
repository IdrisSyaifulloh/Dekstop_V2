"""
Script untuk menggunakan model ONNX maldebCNN untuk inference
Untuk laporan magang - MangoDefend Project
Author: Saefu
Date: 2026-01-01
"""

import onnxruntime as ort
import numpy as np
from PIL import Image
from torchvision import transforms
import os

# ============================================
# KONFIGURASI
# ============================================
ONNX_MODEL_PATH = 'maldebCNN.onnx'
IMAGE_SIZE = (224, 224)
CLASS_NAMES = ['Benign', 'Malware']

# ============================================
# PREPROCESSING
# ============================================
def preprocess_image(image_path):
    """
    Preprocessing image sesuai dengan format training
    
    Args:
        image_path: Path ke image file
        
    Returns:
        numpy array yang siap untuk inference
    """
    # Define transformasi (sama seperti saat training)
    transform = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.ToTensor(),
    ])
    
    # Load dan convert image
    image = Image.open(image_path).convert('RGB')
    
    # Apply transformasi
    input_tensor = transform(image)
    
    # Add batch dimension dan convert ke numpy
    input_batch = input_tensor.unsqueeze(0).numpy()
    
    return input_batch

# ============================================
# INFERENCE FUNCTION
# ============================================
def predict_malware(image_path, ort_session):
    """
    Melakukan prediksi apakah file adalah malware atau benign
    
    Args:
        image_path: Path ke image file (spectrogram)
        ort_session: ONNX Runtime session
        
    Returns:
        tuple: (prediction_class, confidence_score)
    """
    # Preprocess image
    input_batch = preprocess_image(image_path)
    
    # Get input/output names
    input_name = ort_session.get_inputs()[0].name
    output_name = ort_session.get_outputs()[0].name
    
    # Run inference
    outputs = ort_session.run([output_name], {input_name: input_batch})
    
    # Get prediction
    logits = outputs[0][0]  # Get first (and only) batch
    
    # Apply softmax untuk mendapatkan probabilities
    exp_logits = np.exp(logits - np.max(logits))  # Untuk numerical stability
    probabilities = exp_logits / np.sum(exp_logits)
    
    # Get predicted class
    predicted_class = np.argmax(probabilities)
    confidence = probabilities[predicted_class]
    
    return CLASS_NAMES[predicted_class], confidence, probabilities

# ============================================
# MAIN FUNCTION
# ============================================
def main():
    print("="*60)
    print("MALWARE DETECTION USING ONNX MODEL")
    print("="*60)
    
    # Check if model exists
    if not os.path.exists(ONNX_MODEL_PATH):
        print(f"\nERROR: Model file '{ONNX_MODEL_PATH}' tidak ditemukan!")
        print("Silakan jalankan script 'convert_to_onnx.py' terlebih dahulu.")
        return
    
    # Load ONNX model
    print(f"\nLoading ONNX model from '{ONNX_MODEL_PATH}'...")
    ort_session = ort.InferenceSession(ONNX_MODEL_PATH)
    print("✓ Model loaded successfully!")
    
    # Display model info
    print(f"\nModel Information:")
    print(f"  Input name: {ort_session.get_inputs()[0].name}")
    print(f"  Input shape: {ort_session.get_inputs()[0].shape}")
    print(f"  Output name: {ort_session.get_outputs()[0].name}")
    print(f"  Output shape: {ort_session.get_outputs()[0].shape}")
    
    # Example: Predict single image
    print("\n" + "="*60)
    print("SINGLE IMAGE PREDICTION")
    print("="*60)
    
    # Ganti dengan path ke image yang ingin diprediksi
    test_image = input("\nMasukkan path ke image file (atau tekan Enter untuk skip): ").strip()
    
    if test_image and os.path.exists(test_image):
        try:
            print(f"\nProcessing image: {test_image}")
            prediction, confidence, probabilities = predict_malware(test_image, ort_session)
            
            print(f"\nHasil Prediksi:")
            print(f"  Kelas: {prediction}")
            print(f"  Confidence: {confidence*100:.2f}%")
            print(f"\nProbabilities:")
            for i, class_name in enumerate(CLASS_NAMES):
                print(f"  {class_name}: {probabilities[i]*100:.2f}%")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
    else:
        print("\nSkipping single image prediction.")
    
    # Example: Batch prediction
    print("\n" + "="*60)
    print("BATCH PREDICTION")
    print("="*60)
    
    test_folder = input("\nMasukkan path ke folder dengan images (atau tekan Enter untuk skip): ").strip()
    
    if test_folder and os.path.exists(test_folder):
        print(f"\nProcessing images in folder: {test_folder}")
        
        # Get all image files
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
        image_files = [
            os.path.join(test_folder, f) 
            for f in os.listdir(test_folder) 
            if os.path.splitext(f)[1].lower() in image_extensions
        ]
        
        if not image_files:
            print("Tidak ada image file ditemukan di folder tersebut.")
        else:
            print(f"Ditemukan {len(image_files)} images.")
            
            # Process each image
            results = []
            for i, image_path in enumerate(image_files, 1):
                try:
                    prediction, confidence, _ = predict_malware(image_path, ort_session)
                    results.append({
                        'file': os.path.basename(image_path),
                        'prediction': prediction,
                        'confidence': confidence
                    })
                    print(f"  [{i}/{len(image_files)}] {os.path.basename(image_path)}: {prediction} ({confidence*100:.2f}%)")
                except Exception as e:
                    print(f"  [{i}/{len(image_files)}] {os.path.basename(image_path)}: ERROR - {str(e)}")
            
            # Summary
            if results:
                malware_count = sum(1 for r in results if r['prediction'] == 'Malware')
                benign_count = sum(1 for r in results if r['prediction'] == 'Benign')
                
                print(f"\nSummary:")
                print(f"  Total files: {len(results)}")
                print(f"  Malware: {malware_count}")
                print(f"  Benign: {benign_count}")
    else:
        print("\nSkipping batch prediction.")
    
    print("\n" + "="*60)
    print("SELESAI")
    print("="*60)

if __name__ == "__main__":
    main()
