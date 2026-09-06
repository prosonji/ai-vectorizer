"""
Vectorizer Engine (Step 7 - Color Support, Step 15 - Optimize Presets)

এই ফাইল হলো আমাদের প্রজেক্টের "মূল ইঞ্জিন" - এখানেই আসল
ছবি-থেকে-ভেক্টর রূপান্তরের কাজ হয়।

Step 15 (নতুন) - "Optimize for" প্রিসেট:
    ইউজার এখন vectorizer.ai এর মতো "Optimize for" প্রিসেট বাছাই
    করতে পারবে - general use / easy editing / cutting & engraving /
    custom। প্রতিটা প্রিসেট mode আর epsilon_ratio (কার্ভ কতটা সরল
    করা হবে, মানে কতগুলো anchor point থাকবে) এর একটা নির্দিষ্ট
    কম্বিনেশন ব্যবহার করে। "custom" দিলে ইউজারের দেওয়া mode/
    epsilon_ratio হুবহু ব্যবহার হয় - কোনো প্রিসেট চাপিয়ে দেওয়া হয় না।
"""

import cv2
import numpy as np
import svgwrite


# ============================================================
# Step 15: "Optimize for" প্রিসেট
# ============================================================

# প্রতিটা প্রিসেট -> (mode, epsilon_ratio) এর একটা নির্দিষ্ট কম্বিনেশন।
# epsilon_ratio যত বেশি, কার্ভ তত বেশি "সরল" হবে (কম anchor point,
# সম্পাদনা করা সহজ, কিন্তু আসল shape এর সাথে সামান্য কম মিল থাকবে)।
PRESETS = {
    "general": {"mode": "bw", "epsilon_ratio": 0.004},
    "editing": {"mode": "bw", "epsilon_ratio": 0.010},
    "cutting": {"mode": "bw", "epsilon_ratio": 0.006},
}

DEFAULT_EPSILON_RATIO = 0.004


def resolve_optimize_settings(
    optimize_for: str, mode: str, epsilon_ratio: float | None
) -> tuple[str, float]:
    """
    "optimize_for" প্রিসেট আর ইউজারের দেওয়া mode/epsilon_ratio মিলিয়ে
    আসল (mode, epsilon_ratio) বের করে দেয়।

    - optimize_for == "custom": ইউজারের দেওয়া mode হুবহু ব্যবহার হয়,
      epsilon_ratio দেওয়া থাকলে সেটা, না দিলে DEFAULT_EPSILON_RATIO।
    - অন্য কোনো প্রিসেট (general/editing/cutting): সেই প্রিসেটের
      mode + epsilon_ratio ব্যবহার হয় (ইউজারের mode/epsilon_ratio
      উপেক্ষা করা হয়, যাতে প্রিসেট সত্যিকারের প্রিসেট হিসেবে কাজ করে)।
    """
    if optimize_for == "custom":
        return mode, epsilon_ratio if epsilon_ratio is not None else DEFAULT_EPSILON_RATIO

    preset = PRESETS.get(optimize_for, PRESETS["general"])
    return preset["mode"], preset["epsilon_ratio"]


# ============================================================
# ধাপ ১: ছবি লোড করা (দুই মোডেই ব্যবহার হয়)
# ============================================================

def load_image(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"ছবিটা পড়া যায়নি: {image_path}")
    return image


# ============================================================
# Black & White মোডের জন্য ফাংশন
# ============================================================

def to_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def reduce_noise(gray_image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(gray_image, (5, 5), 0)


def threshold_image(gray_image: np.ndarray) -> np.ndarray:
    _, binary = cv2.threshold(
        gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    return binary


# ============================================================
# Color মোডের জন্য নতুন ফাংশন (Step 7)
# ============================================================

def quantize_colors(image: np.ndarray, num_colors: int = 8):
    height, width = image.shape[:2]
    smoothed = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
    pixel_data = smoothed.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    _, labels, centers = cv2.kmeans(
        pixel_data,
        num_colors,
        None,
        criteria,
        attempts=3,
        flags=cv2.KMEANS_PP_CENTERS,
    )

    centers = np.uint8(centers)
    labels_2d = labels.reshape((height, width))

    return labels_2d, centers


def bgr_to_hex(bgr_color) -> str:
    b, g, r = int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])
    return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# Contour খোঁজা ও shape বানানো - দুই মোডেই কমন লজিক
# ============================================================

def find_contours_with_hierarchy(binary_image: np.ndarray):
    contours, hierarchy = cv2.findContours(
        binary_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours, hierarchy


def simplify_contour(contour, epsilon_ratio: float = DEFAULT_EPSILON_RATIO):
    """
    Step 15 আপডেট: epsilon_ratio এখন একটা parameter - "Optimize for"
    প্রিসেট অনুযায়ী এই মান বদলায় (general=0.004, editing=0.010,
    cutting=0.006)। যত বেশি epsilon_ratio, তত বেশি "অপ্রয়োজনীয়"
    পয়েন্ট বাদ দেওয়া হয় (anchor point কমে, edit করা সহজ হয়),
    কিন্তু shape এর মূল আকৃতির সাথে সূক্ষ্ম পার্থক্য একটু বাড়ে।
    """
    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_ratio * perimeter
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    return simplified


def _catmull_rom_to_bezier_path(points) -> str:
    n = len(points)
    if n < 3:
        path_data = f"M {points[0][0]},{points[0][1]} "
        for x, y in points[1:]:
            path_data += f"L {x},{y} "
        path_data += "Z "
        return path_data

    path_data = f"M {points[0][0]},{points[0][1]} "

    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i % n]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]

        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0

        path_data += (
            f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f} "
        )

    path_data += "Z "
    return path_data


def _contour_to_smooth_path_segment(contour, epsilon_ratio: float = DEFAULT_EPSILON_RATIO) -> str:
    simplified = simplify_contour(contour, epsilon_ratio=epsilon_ratio)
    points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]

    if len(points) < 2:
        return ""

    return _catmull_rom_to_bezier_path(points)


def build_shape_paths(
    binary_image: np.ndarray,
    min_area: float = 0.0,
    epsilon_ratio: float = DEFAULT_EPSILON_RATIO,
):
    """
    epsilon_ratio: Step 15 - "Optimize for" প্রিসেট অনুযায়ী কার্ভ
    কতটা সরল হবে সেটা নিয়ন্ত্রণ করে (দেখো simplify_contour)।
    """
    contours, hierarchy = find_contours_with_hierarchy(binary_image)

    paths = []
    seen_paths = set()

    if hierarchy is None:
        return paths

    hierarchy = hierarchy[0]
    hole_min_area = min_area / 4 if min_area > 0 else 0

    for i, contour in enumerate(contours):
        parent_index = hierarchy[i][3]

        if parent_index != -1:
            continue

        if len(contour) < 3:
            continue

        if min_area > 0 and cv2.contourArea(contour) < min_area:
            continue

        path_data = _contour_to_smooth_path_segment(contour, epsilon_ratio=epsilon_ratio)
        if not path_data:
            continue

        for j, child_contour in enumerate(contours):
            if hierarchy[j][3] != i or len(child_contour) < 3:
                continue
            if hole_min_area > 0 and cv2.contourArea(child_contour) < hole_min_area:
                continue
            child_path = _contour_to_smooth_path_segment(child_contour, epsilon_ratio=epsilon_ratio)
            if child_path:
                path_data += child_path

        if path_data in seen_paths:
            continue
        seen_paths.add(path_data)

        paths.append(path_data)

    return paths


# ============================================================
# Black & White মোডের মূল পাইপলাইন
# ============================================================

def vectorize_image_bw(
    input_path: str,
    output_svg_path: str,
    epsilon_ratio: float = DEFAULT_EPSILON_RATIO,
) -> dict:
    """
    Step 15: epsilon_ratio এখন প্যারামিটার - "Optimize for" প্রিসেট
    অনুযায়ী এটা general/editing/cutting এর জন্য আলাদা আলাদা মান পায়।
    """
    image = load_image(input_path)
    height, width = image.shape[:2]

    gray = to_grayscale(image)
    denoised = reduce_noise(gray)
    binary = threshold_image(denoised)

    min_area = (width * height) * 0.0002

    paths = build_shape_paths(binary, min_area=min_area, epsilon_ratio=epsilon_ratio)

    dwg = svgwrite.Drawing(output_svg_path, size=(width, height))
    for path_data in paths:
        dwg.add(
            dwg.path(d=path_data, fill="black", stroke="none", fill_rule="evenodd")
        )
    dwg.save()

    return {
        "width": width,
        "height": height,
        "shapes_found": len(paths),
        "mode": "bw",
    }


# ============================================================
# Color মোডের মূল পাইপলাইন (Step 7 - নতুন)
# ============================================================

def vectorize_image_color(
    input_path: str,
    output_svg_path: str,
    num_colors: int = 8,
    epsilon_ratio: float = DEFAULT_EPSILON_RATIO,
) -> dict:
    """
    Step 15: epsilon_ratio প্যারামিটার যোগ হলো, "Optimize for" প্রিসেট
    অনুযায়ী কার্ভ simplify করার পরিমাণ নিয়ন্ত্রণ করে।
    """
    image = load_image(input_path)
    height, width = image.shape[:2]

    labels_2d, centers = quantize_colors(image, num_colors=num_colors)

    min_area = (width * height) * 0.0005

    dwg = svgwrite.Drawing(output_svg_path, size=(width, height))
    total_shapes = 0
    colors_used = 0

    cluster_sizes = []
    for cluster_index in range(num_colors):
        pixel_count = int(np.sum(labels_2d == cluster_index))
        cluster_sizes.append((cluster_index, pixel_count))

    cluster_sizes.sort(key=lambda item: item[1], reverse=True)
    ordered_cluster_indices = [idx for idx, _count in cluster_sizes]

    dilate_kernel = np.ones((3, 3), np.uint8)

    for cluster_index in ordered_cluster_indices:
        mask = np.uint8(labels_2d == cluster_index) * 255

        if not np.any(mask):
            continue

        mask = cv2.dilate(mask, dilate_kernel, iterations=1)

        paths = build_shape_paths(mask, min_area=min_area, epsilon_ratio=epsilon_ratio)
        if not paths:
            continue

        colors_used += 1
        fill_color = bgr_to_hex(centers[cluster_index])

        for path_data in paths:
            dwg.add(
                dwg.path(
                    d=path_data,
                    fill=fill_color,
                    stroke="none",
                    fill_rule="evenodd",
                )
            )
            total_shapes += 1

    dwg.save()

    return {
        "width": width,
        "height": height,
        "shapes_found": total_shapes,
        "colors_used": colors_used,
        "mode": "color",
    }


# ============================================================
# প্রধান এন্ট্রি পয়েন্ট - app/api/vectorize.py এখান থেকে কল করবে
# ============================================================

def vectorize_image(
    input_path: str,
    output_svg_path: str,
    mode: str = "bw",
    num_colors: int = 8,
    optimize_for: str = "general",
    epsilon_ratio: float | None = None,
) -> dict:
    """
    Step 15: এখন optimize_for প্রিসেট (general/editing/cutting/custom)
    অনুযায়ী প্রথমে আসল (mode, epsilon_ratio) বের করা হয়
    (resolve_optimize_settings দিয়ে), তারপর সেই অনুযায়ী সঠিক
    পাইপলাইন (bw বা color) চালানো হয়।
    """
    resolved_mode, resolved_epsilon = resolve_optimize_settings(
        optimize_for, mode, epsilon_ratio
    )

    result = (
        vectorize_image_color(
            input_path, output_svg_path, num_colors=num_colors, epsilon_ratio=resolved_epsilon
        )
        if resolved_mode == "color"
        else vectorize_image_bw(input_path, output_svg_path, epsilon_ratio=resolved_epsilon)
    )
    result["optimize_for"] = optimize_for
    return result


# ============================================================
# Step 11: DXF export এর জন্য - shape গুলোকে polygon (পয়েন্টের
# লিস্ট) আকারে বের করা
# ============================================================

def extract_polygons_for_dxf(input_path: str):
    image = load_image(input_path)
    height, width = image.shape[:2]

    gray = to_grayscale(image)
    denoised = reduce_noise(gray)
    binary = threshold_image(denoised)

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    min_area = (width * height) * 0.0002
    polygons = []

    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        simplified = simplify_contour(contour)
        points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]
        if len(points) >= 3:
            polygons.append(points)

    return polygons, width, height
