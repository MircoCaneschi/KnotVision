from core.ai.ai_analyzer_base import BaseAIAnalyzer
from core.ai.ai_models import AIAnalysisResult, BoardFaceInfo, AiKnotSegment, Point2D
from core.path_utils import get_resource_path, safe_read_image
import torch
import cv2
import numpy as np
import os
import uuid
from typing import List, Tuple, Optional

class Sam2Analyzer(BaseAIAnalyzer):
    def __init__(self, model_cfg="configs/sam2.1/sam2.1_hiera_s.yaml", model_ckpt="models/sam2.1_hiera_small.pt"):
        self.model_cfg = model_cfg
        self.model_ckpt = str(get_resource_path(model_ckpt))
        self.mask_generator = None
        self.device = None
        self._use_autocast = False
        
        # SAM2 configuration parameters - high recall & irregular shapes, strict darkness filter
        self.points_per_side = 32
        self.points_per_batch = 64
        self.pred_iou_thresh = 0.40
        self.stability_score_thresh = 0.70
        self.crop_n_layers = 0
        self.min_mask_region_area = 50
        self.max_edge = 1024
        
        # Post-filtering parameters
        self.min_knot_area_px = 30
        self.max_knot_area_ratio = 0.10  # A knot shouldn't exceed 10% of total board area
        self.max_brightness_ratio = 0.85  # Knot must be at least 15% darker than surrounding wood
        self.max_overlap_ratio = 0.05     # Discard masks overlapping > 5% with higher-scoring masks
        
    def load_model(self) -> None:
        # Skip if already loaded
        if self.mask_generator is not None:
            return

        resolved_ckpt = get_resource_path(self.model_ckpt)
        if not resolved_ckpt.exists():
            raise FileNotFoundError(f"Model weights not found at '{self.model_ckpt}' (resolved as '{resolved_ckpt}'). Please ensure they are downloaded.")
        self.model_ckpt = str(resolved_ckpt)
            
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
        from sam2.build_sam import build_sam2
            
        # Hardware detection
        self.device = torch.device("cpu")
        if torch.cuda.is_available():
            try:
                _ = torch.cuda.device_count()
                self.device = torch.device("cuda")
                if torch.cuda.get_device_capability()[0] >= 8:
                    self._use_autocast = True
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
            except Exception as e:
                print(f"Sam2Analyzer: CUDA check failed ({e}). Falling back to CPU.")
                self.device = torch.device("cpu")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
            
        print(f"Sam2Analyzer: Loading model '{self.model_cfg}' on device: {self.device}...")
        sam2_model = build_sam2(self.model_cfg, self.model_ckpt, device=self.device)
        self.mask_generator = SAM2AutomaticMaskGenerator(
            model=sam2_model,
            points_per_side=self.points_per_side,
            points_per_batch=self.points_per_batch,
            pred_iou_thresh=self.pred_iou_thresh,
            stability_score_thresh=self.stability_score_thresh,
            crop_n_layers=self.crop_n_layers,
            min_mask_region_area=self.min_mask_region_area,
        )
        print("Sam2Analyzer: Model loaded successfully.")

    def _detect_wood_crop_bounds(self, img_rgb: np.ndarray) -> Tuple[int, int]:
        """
        Phase 1A: Detect top and bottom boundaries of the wood region.
        Crops out non-wood artifacts (e.g. grey/white calibration strips at bottom).
        Wood has warm color (R > G > B with R - B > 14) and Saturation > 20.
        """
        height, width = img_rgb.shape[:2]
        
        r = img_rgb[:, :, 0].astype(np.float32)
        g = img_rgb[:, :, 1].astype(np.float32)
        b = img_rgb[:, :, 2].astype(np.float32)
        
        rb_diff_row = np.mean(r - b, axis=1)
        
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        sat_row = np.mean(hsv[:, :, 1], axis=1)
        val_row = np.mean(hsv[:, :, 2], axis=1)
        
        # Row is wood if warm R-B > 14 and Saturation > 20, and NOT bright desaturated grey/white
        is_wood_row = (rb_diff_row > 14.0) & (sat_row > 20.0) & (~((val_row > 190) & (sat_row < 35)))
        
        # Scan from bottom upwards to find bottom boundary of wood
        bottom_y = height
        for y in range(height - 1, int(height * 0.5), -1):
            if is_wood_row[y]:
                bottom_y = y + 1
                break
                
        # Scan from top downwards
        top_y = 0
        for y in range(0, int(height * 0.5)):
            if is_wood_row[y]:
                top_y = y
                break
                
        print(f"Sam2Analyzer: Detected wood crop bounds: top={top_y}, bottom={bottom_y} (total height: {height}px)")
        return top_y, bottom_y

    def _detect_face_divisions(self, wood_rgb: np.ndarray, board_height: float = 0, board_base: float = 0) -> List[BoardFaceInfo]:
        """
        Phase 1B: Detect horizontal seam divisions between board faces using horizontal projection.
        Uses physical board dimensions (height H, base B) to calculate expected split ratios:
        - Split 1 (Face 1/2): H / (2H + 2B)
        - Split 2 (Face 2/3): (H + B) / (2H + 2B) = 0.50 (exact middle)
        - Split 3 (Face 3/4): (2H + B) / (2H + 2B) = 1.0 - Split 1
        """
        height, width = wood_rgb.shape[:2]
        
        # Calculate theoretical splits based on physical board dimensions
        if board_height > 0 and board_base > 0:
            total_perim = 2 * board_height + 2 * board_base
            ratio1 = board_height / total_perim
            ratio2 = 0.50
            ratio3 = (2 * board_height + board_base) / total_perim
        else:
            # Default approximation: Face 1 & 3 narrower (15% height each)
            ratio1, ratio2, ratio3 = 0.15, 0.50, 0.85

        gray = cv2.cvtColor(wood_rgb, cv2.COLOR_RGB2GRAY)
        row_intensity = np.mean(gray, axis=1)
        
        kernel_size = max(5, int(height * 0.01) | 1)
        smoothed = cv2.GaussianBlur(row_intensity.astype(np.float32), (kernel_size, 1), 0).flatten()
        
        expected_ratios = [ratio1, ratio2, ratio3]
        splits = []
        
        for exp in expected_ratios:
            exp_y = int(height * exp)
            # Tighter search margin for the middle 50% split, broader for 1st and 3rd splits
            margin_ratio = 0.04 if abs(exp - 0.50) < 0.01 else 0.08
            margin = int(height * margin_ratio)
            
            y_min = max(0, exp_y - margin)
            y_max = min(height - 1, exp_y + margin)
            
            if y_max > y_min:
                min_y = y_min + int(np.argmin(smoothed[y_min:y_max]))
            else:
                min_y = exp_y
            splits.append(float(min_y))
            
        y_boundaries = [0.0] + splits + [float(height)]
        faces = []
        for i in range(1, 5):
            faces.append(BoardFaceInfo(
                face_id=i,
                min_y=y_boundaries[i-1],
                max_y=y_boundaries[i]
            ))
        return faces

    def _is_dark_knot(self, mask_bool: np.ndarray, gray_img: np.ndarray, bbox: list = None) -> bool:
        """
        Phase 3: Verify if a segment is a genuine dark knot by comparing its brightness
        against the immediate surrounding wood background.
        Optimized with local bounding box sub-cropping for fast computation.
        """
        if bbox is not None:
            x, y, w, h = bbox
            pad = 15
            y0, y1 = max(0, int(y) - pad), min(gray_img.shape[0], int(y + h) + pad)
            x0, x1 = max(0, int(x) - pad), min(gray_img.shape[1], int(x + w) + pad)
            crop_gray = gray_img[y0:y1, x0:x1]
            crop_mask = mask_bool[y0:y1, x0:x1]
        else:
            crop_gray = gray_img
            crop_mask = mask_bool

        mask_pixels = crop_gray[crop_mask]
        if len(mask_pixels) == 0:
            return False
            
        mean_knot = float(np.mean(mask_pixels))
        
        mask_uint8 = (crop_mask * 255).astype(np.uint8)
        kernel = np.ones((13, 13), np.uint8)
        dilated_mask = cv2.dilate(mask_uint8, kernel, iterations=2)
        bg_bool = (dilated_mask > 0) & (~crop_mask)
        
        bg_pixels = crop_gray[bg_bool]
        if len(bg_pixels) == 0:
            return True
            
        mean_bg = float(np.mean(bg_pixels))
        if mean_bg < 1.0:
            return False
            
        ratio = mean_knot / mean_bg
        # Knot must be significantly darker than local background (ratio <= 0.88)
        return ratio <= self.max_brightness_ratio

    def _filter_overlapping_masks(self, masks: List[dict], max_overlap_ratio: float = 0.05) -> List[dict]:
        """
        Phase 3B: Non-Maximum Suppression (NMS).
        Optimized with bounding box fast-path check before full pixel matrix operations.
        """
        # Sort masks by predicted IoU / confidence score (descending)
        sorted_masks = sorted(masks, key=lambda m: m.get('predicted_iou', 0.0), reverse=True)
        
        filtered = []
        for curr in sorted_masks:
            curr_bool = curr['segmentation']
            curr_area = curr['area']
            if curr_area <= 0:
                continue
                
            curr_bbox = curr.get('bbox')
            is_overlap = False
            for accepted in filtered:
                acc_area = accepted['area']
                acc_bbox = accepted.get('bbox')
                
                # Bounding box fast-path check
                if curr_bbox and acc_bbox:
                    x1, y1, w1, h1 = curr_bbox
                    x2, y2, w2, h2 = acc_bbox
                    if (x1 + w1 <= x2) or (x2 + w2 <= x1) or (y1 + h1 <= y2) or (y2 + h2 <= y1):
                        continue

                acc_bool = accepted['segmentation']
                # Compute intersection
                intersection = np.logical_and(curr_bool, acc_bool)
                inter_area = np.sum(intersection)
                
                if inter_area <= 0:
                    continue
                    
                # Overlap ratio relative to the smaller mask area
                overlap_ratio = inter_area / float(min(curr_area, acc_area))
                
                if overlap_ratio > max_overlap_ratio:
                    is_overlap = True
                    break
                    
            if not is_overlap:
                filtered.append(curr)
                
        return filtered

    def analyze(self, image_path: str, board_length: int, board_base: int, board_height: int, test_position: int = 0, cancel_checker=None) -> Optional[AIAnalysisResult]:
        if cancel_checker and cancel_checker():
            print("Sam2Analyzer: Analysis cancelled before model loading.")
            return None

        if self.mask_generator is None:
            print("Sam2Analyzer: Auto-loading model...")
            self.load_model()
            
        print(f"Sam2Analyzer: Analyzing {image_path} (Test Position: {test_position}mm)...")
        
        img_bgr = safe_read_image(image_path)
        if img_bgr is None:
            raise ValueError(f"Could not read image at {image_path}")
            
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # --- Phase 1A: Crop Non-Wood Regions (grey strip at bottom) ---
        top_y, bottom_y = self._detect_wood_crop_bounds(img_rgb)
        wood_rgb = img_rgb[top_y:bottom_y, :]
        wood_height, wood_width = wood_rgb.shape[:2]
        
        # --- Phase 1B: Detect Board Face Division Lines ---
        faces_crop = self._detect_face_divisions(wood_rgb, board_height=board_height, board_base=board_base)
        
        # --- Phase 1C: Restrict Analysis to TestPos ROI if specified ---
        testpos_crop_x0 = 0
        if test_position and test_position > 0 and board_length > 0:
            px_per_mm_x = wood_width / float(board_length)
            min_x_mm = max(0, test_position - (3 * board_height))
            max_x_mm = min(board_length, test_position + (3 * board_height))
            
            min_x_px = int(min_x_mm * px_per_mm_x)
            max_x_px = int(max_x_mm * px_per_mm_x)
            
            if max_x_px > min_x_px:
                wood_rgb = wood_rgb[:, min_x_px:max_x_px]
                testpos_crop_x0 = min_x_px
                print(f"Sam2Analyzer: Restricted analysis to TestPos ROI [{min_x_px}px : {max_x_px}px] (ROI width: {wood_rgb.shape[1]}px vs total: {wood_width}px)")
        
        # --- Resize wood ROI image for fast SAM2 inference ---
        scale_factor = 1.0
        roi_h, roi_w = wood_rgb.shape[:2]
        longest_edge = max(roi_h, roi_w)
        if longest_edge > self.max_edge:
            scale_factor = self.max_edge / longest_edge
            new_w = int(roi_w * scale_factor)
            new_h = int(roi_h * scale_factor)
            proc_rgb = cv2.resize(wood_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            proc_rgb = wood_rgb.copy()

        proc_h, proc_w = proc_rgb.shape[:2]
        proc_gray = cv2.cvtColor(proc_rgb, cv2.COLOR_RGB2GRAY)
        
        # --- SAM2 prompt grid density ---
        target_pps = self.points_per_side
        try:
            from sam2.automatic_mask_generator import build_all_layer_point_grids
            self.mask_generator.point_grids = build_all_layer_point_grids(
                target_pps,
                self.crop_n_layers,
                1
            )
        except Exception:
            pass

        if cancel_checker and cancel_checker():
            print("Sam2Analyzer: Analysis cancelled before SAM2 inference.")
            return None

        print(f"Sam2Analyzer: Running SAM2 inference (Points per side: {target_pps}, Total points: {target_pps * target_pps})...")

        # --- Phase 2: Run SAM2 Mask Generator on ROI ---
        with torch.inference_mode():
            if self._use_autocast:
                with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                    raw_masks = self.mask_generator.generate(proc_rgb)
            else:
                raw_masks = self.mask_generator.generate(proc_rgb)
            
        if cancel_checker and cancel_checker():
            print("Sam2Analyzer: Analysis cancelled after SAM2 inference.")
            return None

        print(f"Sam2Analyzer: Raw masks generated in ROI: {len(raw_masks)}")
        
        # --- Phase 3A: Post-processing & Darkness Filtering ---
        candidate_masks = []
        max_area_px = proc_w * proc_h * self.max_knot_area_ratio
        
        for mask_data in raw_masks:
            if cancel_checker and cancel_checker():
                print("Sam2Analyzer: Analysis cancelled during mask filtering.")
                return None

            mask_bool = mask_data['segmentation']
            area = mask_data['area']
            
            # Area filter
            if area < self.min_knot_area_px or area > max_area_px:
                continue
                
            # Darkness filter
            if not self._is_dark_knot(mask_bool, proc_gray, bbox=mask_data.get('bbox')):
                continue
                
            candidate_masks.append(mask_data)
            
        # --- Phase 3B: Overlap Suppression (NMS > 5% area overlap) ---
        retained_masks = self._filter_overlapping_masks(candidate_masks, max_overlap_ratio=self.max_overlap_ratio)
        print(f"Sam2Analyzer: NMS filter reduced {len(candidate_masks)} candidates to {len(retained_masks)} unique knot masks.")

        segments = []
        for mask_data in retained_masks:
            if cancel_checker and cancel_checker():
                print("Sam2Analyzer: Analysis cancelled during polygon conversion.")
                return None

            mask_bool = mask_data['segmentation']
            
            # Contour extraction & preservation of fine irregular shapes
            mask_uint8 = (mask_bool * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
                
            largest_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.002 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            if len(approx) < 3:
                continue
                
            # Convert contour points to full wood image coordinates (adding testpos offset)
            inv_scale = 1.0 / scale_factor
            poly = []
            for pt in approx:
                x_orig = (float(pt[0][0]) * inv_scale) + testpos_crop_x0
                y_orig = float(pt[0][1]) * inv_scale
                poly.append(Point2D(x=x_orig, y=y_orig))
                
            # Assign face based on average Y in crop space
            cy_crop = np.mean([pt[0][1] for pt in approx]) * inv_scale
            assigned_face = 1
            for f in faces_crop:
                if f.min_y <= cy_crop <= f.max_y:
                    assigned_face = f.face_id
                    break
                    
            segments.append(AiKnotSegment(
                segment_id=str(uuid.uuid4()),
                polygon=poly,
                face_id=assigned_face,
                confidence=round(float(mask_data.get('predicted_iou', 1.0)), 3)
            ))
            
        print(f"Sam2Analyzer: {len(segments)} final non-overlapping knot segments retained in ROI.")
        
        return AIAnalysisResult(
            image_width=wood_width,
            image_height=wood_height,
            faces=faces_crop,
            segments=segments
        )
