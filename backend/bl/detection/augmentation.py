from __future__ import annotations

import random
import cv2
import numpy as np


class MotionBlur:
    """Simulates motion blur by applying a directional linear kernel filter."""
    def __init__(self, max_kernel_size: int = 15) -> None:
        self.max_kernel_size = max_kernel_size

    def __call__(self, image: np.ndarray) -> np.ndarray:
        ksize = random.randrange(3, self.max_kernel_size + 1, 2)
        angle = random.uniform(0, 360)
        
        # Create line kernel
        kernel = np.zeros((ksize, ksize), dtype=np.float32)
        center = ksize // 2
        
        # Calculate slope of the line based on the random angle
        rad = np.deg2rad(angle)
        cos_val = np.cos(rad)
        sin_val = np.sin(rad)
        
        for i in range(ksize):
            offset = i - center
            x = int(round(center + offset * cos_val))
            y = int(round(center + offset * sin_val))
            if 0 <= x < ksize and 0 <= y < ksize:
                kernel[y, x] = 1.0
                
        kernel_sum = kernel.sum()
        if kernel_sum > 0:
            kernel /= kernel_sum
        else:
            kernel[center, center] = 1.0
            
        return cv2.filter2D(image, -1, kernel)


class DigitalNoise:
    """Simulates CCTV digital noise by adding Gaussian and/or Salt-and-Pepper noise."""
    def __init__(self, mode: str = "all", var_limit: tuple[float, float] = (10.0, 50.0)) -> None:
        self.mode = mode  # "gaussian", "sp", or "all"
        self.var_limit = var_limit

    def __call__(self, image: np.ndarray) -> np.ndarray:
        mode = self.mode
        if mode == "all":
            mode = random.choice(["gaussian", "sp"])
            
        h, w, c = image.shape
        if mode == "gaussian":
            variance = random.uniform(*self.var_limit)
            sigma = variance ** 0.5
            noise = np.random.normal(0, sigma, (h, w, c))
            noisy = image.astype(np.float32) + noise
            return np.clip(noisy, 0, 255).astype(np.uint8)
        else:
            # Salt and Pepper Noise
            prob = random.uniform(0.01, 0.05)
            noisy = image.copy()
            # Salt (white pixels)
            num_salt = np.ceil(prob * image.size * 0.5)
            coords = [np.random.randint(0, i - 1, int(num_salt)) for i in image.shape]
            noisy[tuple(coords)] = 255
            # Pepper (black pixels)
            num_pepper = np.ceil(prob * image.size * 0.5)
            coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in image.shape]
            noisy[tuple(coords)] = 0
            return noisy


class PerspectiveDistortion:
    """Simulates high CCTV viewing angles and lens distortion via perspective warps."""
    def __init__(self, max_distortion: float = 0.15) -> None:
        self.max_distortion = max_distortion

    def __call__(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        
        # Original 4 corners
        src = np.float32([
            [0, 0],
            [w - 1, 0],
            [w - 1, h - 1],
            [0, h - 1]
        ])
        
        # Randomly perturb 4 corners inward
        dx1 = random.uniform(0, w * self.max_distortion)
        dy1 = random.uniform(0, h * self.max_distortion)
        dx2 = random.uniform(0, w * self.max_distortion)
        dy2 = random.uniform(0, h * self.max_distortion)
        dx3 = random.uniform(0, w * self.max_distortion)
        dy3 = random.uniform(0, h * self.max_distortion)
        dx4 = random.uniform(0, w * self.max_distortion)
        dy4 = random.uniform(0, h * self.max_distortion)
        
        dst = np.float32([
            [dx1, dy1],
            [w - 1 - dx2, dy2],
            [w - 1 - dx3, h - 1 - dy3],
            [dx4, h - 1 - dy4]
        ])
        
        matrix = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(image, matrix, (w, h), borderValue=(114, 114, 114))


class OcclusionSimulation:
    """Simulates occlusions by placing random dark/noise rectangles on the image (cutout)."""
    def __init__(self, max_occlusions: int = 3, size_limit: tuple[float, float] = (0.05, 0.25)) -> None:
        self.max_occlusions = max_occlusions
        self.size_limit = size_limit

    def __call__(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        num_boxes = random.randint(1, self.max_occlusions)
        occluded = image.copy()
        
        for _ in range(num_boxes):
            box_w = int(w * random.uniform(*self.size_limit))
            box_h = int(h * random.uniform(*self.size_limit))
            
            x1 = random.randint(0, max(0, w - box_w))
            y1 = random.randint(0, max(0, h - box_h))
            
            # Use random color or dark gray
            color = random.choice([
                (50, 50, 50),
                (0, 0, 0),
                (128, 128, 128)
            ])
            cv2.rectangle(occluded, (x1, y1), (x1 + box_w, y1 + box_h), color, -1)
            
        return occluded


class VideoStyleAugmentor:
    """Applies a sequence of CCTV-realistic data augmentations to an input image."""
    def __init__(self) -> None:
        self.transforms = [
            MotionBlur(),
            DigitalNoise(),
            PerspectiveDistortion(),
            OcclusionSimulation()
        ]

    def augment(self, image: np.ndarray) -> np.ndarray:
        augmented = image.copy()
        # Randomly choose a subset of transformations to apply
        active_transforms = random.sample(self.transforms, k=random.randint(1, 3))
        for t in active_transforms:
            try:
                augmented = t(augmented)
            except Exception:  # noqa: BLE001
                # Fallback if any transformation fails
                pass
        return augmented
