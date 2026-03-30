import cv2
import numpy as np
import os
from pathlib import Path

def order_points(pts):
    """Order points in top-left, top-right, bottom-right, bottom-left order"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_transform(image, pts):
    """Apply perspective transform to get bird's eye view"""
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def scan_document(image_path, output_folder):
    """Main document scanning function"""
    print(f"\nProcessing: {os.path.basename(image_path)}")
    
    # Read image
    image = cv2.imread(image_path)
    if image is None:
        print(f"  ✗ Failed to load image")
        return False
    
    orig = image.copy()
    ratio = image.shape[0] / 500.0
    image = cv2.resize(image, (int(image.shape[1] / ratio), 500))
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Canny edge detection
    edged = cv2.Canny(blurred, 75, 200)
    
    # Find contours
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    
    screenCnt = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        
        if len(approx) == 4:
            screenCnt = approx
            break
    
    if screenCnt is None:
        print(f"  ✗ Could not find document contour")
        return False
    
    # Apply perspective transform
    warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)
    
    # Convert to grayscale and threshold
    warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    T = cv2.threshold(warped, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    # Save result
    filename = os.path.basename(image_path)
    output_path = os.path.join(output_folder, f"scanned_{filename}")
    cv2.imwrite(output_path, warped)
    
    print(f"  ✓ Successfully scanned! Saved to: {output_path}")
    return True

def main():
    """Process all images in dataset folder"""
    dataset_folder = "."
    output_folder = "output"
    
    # Create output folder
    Path(output_folder).mkdir(exist_ok=True)
    
    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(dataset_folder).glob(f'*{ext}'))
    
    print(f"Found {len(image_files)} images to process\n")
    print("=" * 50)
    
    success_count = 0
    fail_count = 0
    failed_images = []  # ← ADD THIS LINE
    
    # Process all images
    for image_path in list(image_files):
        if scan_document(str(image_path), output_folder):
            success_count += 1
        else:
            fail_count += 1
            failed_images.append(str(image_path))  # ← ADD THIS LINE
    
    print("\n" + "=" * 50)
    print(f"\nRESULTS:")
    print(f"  ✓ Successful: {success_count}")
    print(f"  ✗ Failed: {fail_count}")
    print(f"\nCheck the 'output' folder for scanned documents!")
    
    if failed_images:
        print(f"\n❌ FAILED IMAGES:")
        for img in failed_images:
            print(f"   - {os.path.basename(img)}")


if __name__ == "__main__":
    main()