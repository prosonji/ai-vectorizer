"""
Vectorizer Engine (পুনর্গঠিত - সব ফিচার একসাথে)

⚠️ এই ফাইলটা আগে ভুলবশত অন্য একটা ফাইলের (vectorize.py, API endpoint)
কনটেন্ট দিয়ে বদলে গিয়েছিল। এখন এটা আবার সঠিকভাবে, এতদিন ধরে বানানো
সব ফিচার সহ লেখা হলো।

এই ফাইলে যা যা আছে:
    1. load_image / to_grayscale / reduce_noise / threshold_image
       - মূল preprocessing পাইপলাইন
    2. find_contours_with_hierarchy - shape এর বর্ডার + ভিতরের "গর্ত" (hole) খোঁজা
    3. _adaptive_epsilon_ratio / simplify_contour - shape এর আকৃতি
       (মোটা/সরু) অনুযায়ী automatic ভাবে কতটা সরল (simplify) করা হবে
       ঠিক করা - এটাই "line-art" (পাতলা রেখা যেমন reindeer এর শিং)
       ফিক্স, যেটা সরু shape এ কম simplify করে সূক্ষ্ম ডিটেইল রাখে
    4. _catmull_rom_to_bezier_path - মসৃণ (smooth) SVG curve বানানো
    5. build_shape_paths - একটা mask থেকে সব shape এর SVG path বের করা
    6. quantize_colors / bgr_to_hex - Color মোডের জন্য K-means দিয়ে
       রঙ ভাগ করা
    7. vectorize_image_bw / vectorize_image_color - দুইটা মূল মোড
    8. vectorize_image - সবকিছুর "dispatcher", optimize_for প্রিসেট
       (general/editing/cutting/custom) অনুযায়ী সঠিক সেটিং বেছে নেয়
    9. extract_polygons_for_dxf - DXF export এর জন্য shape এর raw
       পয়েন্ট বের করা (export.py এটা ব্যবহার করে)
"""

import cv2
import numpy as np
import svgwrite


# ============================================================
# ধাপ ১-৪: Preprocessing
# ============================================================

def load_image(image_path: str) -> np.ndarray:
    """ছবিটা ডিস্ক থেকে মেমোরিতে লোড করা।"""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"ছবিটা পড়া যায়নি: {image_path}")
    return image


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """রঙিন ছবিকে সাদা-কালো (grayscale) এ রূপান্তর করা।"""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def reduce_noise(gray_image: np.ndarray) -> np.ndarray:
    """
    ছবির ছোট নয়েজ কমানোর জন্য হালকা blur।

    line-art ফিক্স: kernel size (3,3) - আগে (5,5) ছিল, যেটা পাতলা
    রেখাকে (যেমন reindeer এর শিং) অসমান/ফোলা করে দিচ্ছিল।
    """
    return cv2.GaussianBlur(gray_image, (3, 3), 0)


def threshold_image(gray_image: np.ndarray) -> np.ndarray:
    """
    ছবিকে শুধু কালো (0) আর সাদা (255) এ ভাগ করা - Otsu's method
    দিয়ে automatic ভাবে সঠিক threshold বের করা হয়।
    """
    _, binary = cv2.threshold(
        gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    return binary


# ============================================================
# ধাপ ৫: Contour + Hierarchy (হোল/গর্ত সহ)
# ============================================================

def find_contours_with_hierarchy(binary_image: np.ndarray):
    """
    বাইরের বর্ডার + ভিতরের "গর্ত" (চোখ, মুখ, ডিটেইল) - দুইটাই খুঁজে
    বের করা। RETR_CCOMP দিয়ে দুই-স্তরের hierarchy পাওয়া যায়।
    """
    contours, hierarchy = cv2.findContours(
        binary_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours, hierarchy


# ============================================================
# ধাপ ৬: Adaptive Simplification (line-art ফিক্স)
# ============================================================

def _adaptive_epsilon_ratio(contour) -> float:
    """
    shape কতটা "মোটা/গোলগাল" নাকি "সরু/লম্বা" (যেমন reindeer এর শিং)
    সেটা বিচার করে - সরু shape এ কম epsilon (কম simplify, বেশি
    নিখুঁত/sharp রেখা), মোটা shape এ বেশি epsilon (বেশি smooth)।

    বিচার করে area/perimeter² অনুপাত দিয়ে - কম মানে সরু/লম্বা shape।
    """
    area = cv2.contourArea(contour)
    perimeter = cv2.arcLength(contour, True)

    if perimeter == 0:
        return 0.004

    thinness = area / (perimeter ** 2)

    if thinness < 0.01:
        return 0.0015  # সরু/লম্বা shape - কম simplify

    return 0.004  # মোটাসোটা/গোল shape - বেশি simplify (স্বাভাবিক smooth)


def simplify_contour(contour, epsilon_ratio: float | None = None):
    """
    contour এর মধ্যে থাকা অতিরিক্ত পয়েন্ট বাদ দিয়ে গুরুত্বপূর্ণ কোণার
    পয়েন্ট রাখা (cv2.approxPolyDP)।

    epsilon_ratio=None দিলে shape অনুযায়ী automatic (adaptive) ভাবে
    ঠিক হয়। একটা নির্দিষ্ট মান দিলে (যেমন optimize_for প্রিসেট থেকে)
    সেটাই ব্যবহার হয়, adaptive লজিক উপেক্ষা হয়।
    """
    if epsilon_ratio is None:
        epsilon_ratio = _adaptive_epsilon_ratio(contour)

    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_ratio * perimeter
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    return simplified


# ============================================================
# ধাপ ৭: Smooth Bezier Curve
# ============================================================

def _catmull_rom_to_bezier_path(points) -> str:
    """
    পয়েন্টগুলোর মধ্য দিয়ে একটা মসৃণ, বন্ধ (closed) SVG cubic bezier
    কার্ভ আঁকা - সোজা রেখার (L) বদলে।
    """
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


def _contour_to_smooth_path_segment(contour, epsilon_ratio: float | None = None) -> str:
    """একটা contour কে সরল করে, তারপর মসৃণ bezier path বানানো।"""
    simplified = simplify_contour(contour, epsilon_ratio=epsilon_ratio)
    points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]

    if len(points) < 2:
        return ""

    return _catmull_rom_to_bezier_path(points)


# ============================================================
# ধাপ ৮: Mask থেকে সব Shape এর Path বের করা (bw ও color দুইটাতেই ব্যবহার হয়)
# ============================================================

def build_shape_paths(
    binary_image: np.ndarray,
    min_area: float = 0.0,
    epsilon_ratio: float | None = None,
):
    """
    একটা binary (কালো/সাদা, বা রঙের mask) ছবি থেকে সব shape এর SVG
    path data বের করে লিস্ট হিসেবে ফেরত দেয়। ভিতরের "গর্ত" ঠিকভাবে
    হ্যান্ডেল করা হয় (fill-rule="evenodd" এর জন্য প্রস্তুত করে)।

    duplicate path (হুবহু একই) বাদ দেওয়া হয়।
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
# Color মোডের জন্য - K-means দিয়ে রঙ কমানো
# ============================================================

def quantize_colors(image: np.ndarray, num_colors: int = 8):
    """
    ছবির হাজার হাজার রঙকে K-means clustering দিয়ে num_colors সংখ্যক
    মূল রঙে ভাগ করা। Returns: (labels_2d, centers)
    """
    height, width = image.shape[:2]
    pixels = image.reshape((-1, 3)).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(
        pixels, num_colors, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS
    )

    centers = np.uint8(centers)
    labels_2d = labels.reshape((height, width))
    return labels_2d, centers


def bgr_to_hex(bgr_color) -> str:
    """OpenCV এর BGR রঙকে SVG-বান্ধব hex কোডে (#rrggbb) রূপান্তর করা।"""
    b, g, r = int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])
    return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# মূল দুইটা মোড: Black & White, Color
# ============================================================

def vectorize_image_bw(
    input_path: str,
    output_svg_path: str,
    epsilon_ratio: float | None = None,
) -> dict:
    """Black & White (কালো-সাদা) মোডে ভেক্টরাইজ করা।"""
    image = load_image(input_path)
    height, width = image.shape[:2]

    gray = to_grayscale(image)
    denoised = reduce_noise(gray)
    binary = threshold_image(denoised)

    min_area = (width * height) * 0.0002
    paths = build_shape_paths(binary, min_area=min_area, epsilon_ratio=epsilon_ratio)

    dwg = svgwrite.Drawing(output_svg_path, size=(width, height))
    for path_data in paths:
        dwg.add(dwg.path(d=path_data, fill="black", stroke="none", fill_rule="evenodd"))
    dwg.save()

    return {
        "width": width,
        "height": height,
        "shapes_found": len(paths),
        "colors_used": None,
        "mode": "bw",
    }


def vectorize_image_color(
    input_path: str,
    output_svg_path: str,
    num_colors: int = 8,
    epsilon_ratio: float | None = None,
) -> dict:
    """Color (রঙিন) মোডে ভেক্টরাইজ করা - বড় রঙ আগে, ছোট ডিটেইল রঙ পরে আঁকা হয়।"""
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
            dwg.add(dwg.path(d=path_data, fill=fill_color, stroke="none", fill_rule="evenodd"))
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
# মূল Dispatcher - API থেকে এটাই কল হয়
# ============================================================

# optimize_for প্রিসেট অনুযায়ী epsilon_ratio - vectorizer.ai এর "Optimize
# for" ফিচারের মতো:
#   general  -> None (adaptive, ভারসাম্যপূর্ণ - ডিফল্ট আচরণ)
#   editing  -> বড় epsilon (কম anchor point, সম্পাদনা করা সহজ)
#   cutting  -> ছোট epsilon (বেশি নিখুঁত ডিটেইল, কাটিং/এনগ্রেভিং এর জন্য)
_OPTIMIZE_FOR_EPSILON = {
    "general": None,
    "editing": 0.01,
    "cutting": 0.0025,
}


def vectorize_image(
    input_path: str,
    output_svg_path: str,
    mode: str = "bw",
    num_colors: int = 8,
    optimize_for: str = "general",
) -> dict:
    """
    এটাই API (vectorize.py) থেকে সরাসরি কল হওয়া মূল ফাংশন।

    optimize_for:
        - 'general'/'editing'/'cutting' দিলে প্রিসেট নিজেই mode="bw"
          ঠিক করে দেয় আর তার নিজস্ব epsilon_ratio ব্যবহার করে (mode
          প্যারামিটার উপেক্ষা করা হয়)
        - 'custom' দিলে ইউজারের দেওয়া mode ('bw'/'color') হুবহু মানা
          হয়, আর adaptive (automatic) epsilon ব্যবহার হয়
    """
    if optimize_for in _OPTIMIZE_FOR_EPSILON:
        epsilon_ratio = _OPTIMIZE_FOR_EPSILON[optimize_for]
        result = vectorize_image_bw(input_path, output_svg_path, epsilon_ratio=epsilon_ratio)
    else:
        # optimize_for == "custom" - ইউজারের বাছাই করা mode ব্যবহার হবে
        if mode == "color":
            result = vectorize_image_color(input_path, output_svg_path, num_colors=num_colors)
        else:
            result = vectorize_image_bw(input_path, output_svg_path)

    result["optimize_for"] = optimize_for
    return result


# ============================================================
# DXF export এর জন্য - shape গুলোকে polygon (পয়েন্টের লিস্ট) আকারে বের করা
# ============================================================

def extract_polygons_for_dxf(input_path: str):
    """
    DXF ফরম্যাট Bezier curve সরাসরি সাপোর্ট করে না, তাই সরাসরি ছবি
    থেকে প্রতিটা shape এর "সরল করা" কোণার পয়েন্ট বের করা হয়।

    RETR_LIST ব্যবহার করা হচ্ছে - বাইরের shape আর ভিতরের গর্ত দুইটাই
    আলাদা আলাদা বন্ধ (closed) polygon হিসেবে রাখলেই CNC/লেজার-কাটিং
    সফটওয়্যার এমনিতেই বুঝে নেয়।

    Returns: (polygons, width, height)
    """
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
