"""
Vectorizer Engine (Step 7 - Color Support)

এই ফাইল হলো আমাদের প্রজেক্টের "মূল ইঞ্জিন" - এখানেই আসল
ছবি-থেকে-ভেক্টর রূপান্তরের কাজ হয়।

প্রতিটা ধাপ আলাদা function এ ভাগ করা আছে, যাতে বোঝা সহজ হয়
এবং পরে প্রতিটা ধাপ আলাদাভাবে উন্নত করা যায়।

এখন দুইটা মোড আছে:

    ১) Black & White মোড (Step 3, 5, 6 এ যেটা বানানো হয়েছিল)
       ছবি -> grayscale -> threshold (কালো/সাদা) -> shape বের করা

    ২) Color মোড (Step 7 - নতুন)
       ছবি -> রঙ Quantization (K-means দিয়ে হাজার হাজার রঙকে
       কয়েকটা মূল রঙে ভাগ করা) -> প্রতিটা রঙের জন্য আলাদা mask
       বানিয়ে সেই রঙের shape বের করা -> প্রতিটা shape কে তার
       নিজস্ব রঙ দিয়ে SVG তে আঁকা

দুইটা মোডই "shape বানানোর" মূল লজিক (contour simplify + smooth
curve + hole handling) শেয়ার করে - build_shape_paths() ফাংশনটা
যেকোনো binary (কালো/সাদা) mask থেকে smooth SVG path এর লিস্ট
বানিয়ে দেয়, রঙ নির্বিশেষে।
"""

import cv2
import numpy as np
import svgwrite


# ============================================================
# ধাপ ১: ছবি লোড করা (দুই মোডেই ব্যবহার হয়)
# ============================================================

def load_image(image_path: str) -> np.ndarray:
    """
    ছবিটা ডিস্ক থেকে মেমোরিতে লোড করা।
    OpenCV ছবিকে একটা "numpy array" (সংখ্যার গ্রিড) হিসেবে লোড করে -
    প্রতিটা পিক্সেলের রঙ (B, G, R) একটা করে সংখ্যার সেট।
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"ছবিটা পড়া যায়নি: {image_path}")
    return image


# ============================================================
# Black & White মোডের জন্য ফাংশন
# ============================================================

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    রঙিন ছবিকে সাদা-কালো (grayscale) এ রূপান্তর করা।
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def reduce_noise(gray_image: np.ndarray) -> np.ndarray:
    """
    ছবিতে যদি ছোট ছোট দানা/নয়েজ থাকে, সেটা একটু নরম (blur) করে
    দেওয়া হয়, যাতে পরের ধাপে অপ্রয়োজনীয় ছোট shape তৈরি না হয়।
    """
    return cv2.GaussianBlur(gray_image, (5, 5), 0)


def threshold_image(gray_image: np.ndarray) -> np.ndarray:
    """
    ছবিকে শুধুমাত্র দুই রঙে ভাগ করা - সম্পূর্ণ কালো (0) আর সম্পূর্ণ
    সাদা (255)। Otsu's method automatic ভাবে সঠিক threshold বের করে।
    """
    _, binary = cv2.threshold(
        gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    return binary


# ============================================================
# Color মোডের জন্য নতুন ফাংশন (Step 7)
# ============================================================

def quantize_colors(image: np.ndarray, num_colors: int = 8):
    """
    Step 7 নতুন ফাংশন: ছবির হাজার হাজার রঙকে K-means clustering
    দিয়ে মাত্র কয়েকটা (num_colors সংখ্যক) "মূল রঙে" ভাগ করা।

    কেন দরকার? - একটা সাধারণ ছবিতে প্রায় প্রতিটা পিক্সেলের রঙ একটু
    একটু আলাদা (কারণ camera/rendering এর সূক্ষ্ম pixel পার্থক্য),
    সরাসরি ভেক্টরাইজ করলে হাজার হাজার ছোট ছোট shape তৈরি হয়ে যাবে।
    তাই আগে রঙগুলোকে "গ্রুপ" করে নেওয়া হয় - যেমন সব হালকা লাল
    শেডকে একটাই "লাল" রঙে মিলিয়ে দেওয়া।

    Returns:
        labels_2d: একটা (height, width) আকৃতির গ্রিড, যেখানে প্রতিটা
                   পিক্সেলের জায়গায় লেখা আছে সেটা কোন ক্লাস্টার/রঙে (0 থেকে num_colors-1) পড়েছে
        centers: প্রতিটা ক্লাস্টারের প্রতিনিধি রঙ (BGR ফরম্যাটে)
    """
    height, width = image.shape[:2]

    # প্রথমে একটু blur করে নিচ্ছি (bilateral filter) - এটা edge গুলো
    # ধরে রাখে কিন্তু ভিতরের ছোট রঙের তারতম্য মসৃণ করে দেয়
    smoothed = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

    # K-means এর জন্য ছবিটাকে (pixel_count, 3) আকৃতিতে সাজাতে হয়
    pixel_data = smoothed.reshape((-1, 3)).astype(np.float32)

    # K-means কতবার/কীভাবে থামবে তার নিয়ম
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    _, labels, centers = cv2.kmeans(
        pixel_data,
        num_colors,
        None,
        criteria,
        attempts=3,
        flags=cv2.KMEANS_PP_CENTERS,
    )

    centers = np.uint8(centers)  # রঙের মান (0-255) এ ফিরিয়ে আনা
    labels_2d = labels.reshape((height, width))

    return labels_2d, centers


def bgr_to_hex(bgr_color) -> str:
    """
    OpenCV রঙ রাখে BGR ক্রমে (Blue, Green, Red), কিন্তু SVG/CSS এ
    রঙ লেখা হয় hex ফরম্যাটে (যেমন #ff0000)। এই ফাংশন সেই রূপান্তর করে।
    """
    b, g, r = int(bgr_color[0]), int(bgr_color[1]), int(bgr_color[2])
    return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# Contour খোঁজা ও shape বানানো - দুই মোডেই কমন লজিক
# ============================================================

def find_contours_with_hierarchy(binary_image: np.ndarray):
    """
    বাইনারি (কালো-সাদা/mask) ছবিতে আকৃতির বর্ডার (contour) এর
    পাশাপাশি ভিতরের "গর্ত" (hole) ও খুঁজে বের করা।

    RETR_CCOMP মানে: দুই লেভেলের hierarchy বানাও -
        - বাইরের বর্ডার (parent, hierarchy তে ৩য় value = -1)
        - তার ভিতরের গর্ত (child, hierarchy তে ৩য় value = parent এর index)
    """
    contours, hierarchy = cv2.findContours(
        binary_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    return contours, hierarchy


def simplify_contour(contour, epsilon_ratio: float = 0.004):
    """
    Step 8 আপডেট: epsilon_ratio আগে ছিল 0.003, এখন 0.004 - মানে আগের
    চেয়ে কিছুটা বেশি "অপ্রয়োজনীয়" পয়েন্ট বাদ দেওয়া হয় (anchor point
    কমানো), কিন্তু shape এর মূল আকৃতি প্রায় একই থাকে।

    contour-এর মধ্যে থাকা অতিরিক্ত/অপ্রয়োজনীয় পয়েন্ট বাদ দিয়ে শুধু
    গুরুত্বপূর্ণ কোণার পয়েন্টগুলো রাখা হয় (cv2.approxPolyDP)।
    """
    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_ratio * perimeter
    simplified = cv2.approxPolyDP(contour, epsilon, True)
    return simplified


def _catmull_rom_to_bezier_path(points) -> str:
    """
    পয়েন্টগুলোর মধ্য দিয়ে একটা মসৃণ, বন্ধ (closed) কার্ভ আঁকা -
    সোজা রেখার (L) বদলে SVG cubic bezier কার্ভ (C) ব্যবহার করে
    ("Catmull-Rom to Bezier" পদ্ধতি)।
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


def _contour_to_smooth_path_segment(contour) -> str:
    """
    একটা contour কে - প্রথমে সরল করে (simplify_contour), তারপর
    সেই সরল করা পয়েন্টগুলো দিয়ে মসৃণ bezier path (subpath) বানানো।
    """
    simplified = simplify_contour(contour)
    points = [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]

    if len(points) < 2:
        return ""

    return _catmull_rom_to_bezier_path(points)


def build_shape_paths(binary_image: np.ndarray, min_area: float = 0.0):
    """
    একটা binary (কালো/সাদা, বা রঙের mask) ছবি থেকে সব shape এর
    SVG path data বের করে একটা লিস্ট হিসেবে ফেরত দেয়। এই ফাংশনটা
    Black & White মোড এবং Color মোড - দুই জায়গাতেই ব্যবহার হয়,
    কারণ "shape বের করা"র লজিক দুই মোডেই একই রকম, শুধু ইনপুট mask
    আলাদা।

    min_area: এর চেয়ে ছোট (পিক্সেলে) shape বাদ দেওয়া হবে - এটা
    বিশেষভাবে দরকার Color মোডে, কারণ সেখানে ছোট ছোট নয়েজ-জাতীয়
    অনেক টুকরা shape তৈরি হতে পারে।

    Step 8 আপডেট (SVG cleanup):
        - ভিতরের "গর্ত" (hole) এর জন্যও এখন ছোট area ফিল্টার করা হয়
          (আগে শুধু বাইরের shape ফিল্টার হতো) - এতে খুব ছোট, অদৃশ্য
          "stray" গর্ত/ডট আর SVG তে থেকে যাবে না
        - Duplicate/হুবহু একই path দুইবার যোগ হওয়া বন্ধ করা হয়েছে
    """
    contours, hierarchy = find_contours_with_hierarchy(binary_image)

    paths = []
    seen_paths = set()  # duplicate path সনাক্ত করার জন্য

    if hierarchy is None:
        return paths

    hierarchy = hierarchy[0]

    # গর্তের (hole) জন্য একটু ছোট threshold ব্যবহার করছি (বাইরের shape এর
    # চেয়ে ৪ ভাগের ১ ভাগ) - কারণ চোখ/মুখের মতো ছোট গর্তগুলো বাইরের shape
    # এর চেয়ে স্বাভাবিকভাবেই অনেক ছোট, কিন্তু একদম মাইক্রোস্কোপিক
    # "stray" গর্ত বাদ দেওয়া দরকার
    hole_min_area = min_area / 4 if min_area > 0 else 0

    for i, contour in enumerate(contours):
        parent_index = hierarchy[i][3]

        # শুধু "বাইরের বর্ডার" (top-level shape) থেকে path শুরু করা হবে
        if parent_index != -1:
            continue

        if len(contour) < 3:
            continue

        if min_area > 0 and cv2.contourArea(contour) < min_area:
            continue

        path_data = _contour_to_smooth_path_segment(contour)
        if not path_data:
            continue

        # এই shape এর সব "সন্তান" (গর্ত) খুঁজে একই path এ যোগ করা
        for j, child_contour in enumerate(contours):
            if hierarchy[j][3] != i or len(child_contour) < 3:
                continue
            if hole_min_area > 0 and cv2.contourArea(child_contour) < hole_min_area:
                continue
            child_path = _contour_to_smooth_path_segment(child_contour)
            if child_path:
                path_data += child_path

        # duplicate path হলে (হুবহু একই d= data) স্কিপ করা
        if path_data in seen_paths:
            continue
        seen_paths.add(path_data)

        paths.append(path_data)

    return paths


# ============================================================
# Black & White মোডের মূল পাইপলাইন
# ============================================================

def vectorize_image_bw(input_path: str, output_svg_path: str) -> dict:
    """
    Black & White (কালো-সাদা) মোডে ভেক্টরাইজ করা।

    Step 8 আপডেট: এখন এখানেও একটা ছোট min_area filter যোগ করা হলো
    (আগে এটা শুধু Color মোডে ছিল) - এতে auto-tracing এর সময় তৈরি হওয়া
    অতি ছোট, অবাঞ্ছিত "stray" টুকরা (unwanted vector fragments) বাদ যাবে।
    """
    image = load_image(input_path)
    height, width = image.shape[:2]

    gray = to_grayscale(image)
    denoised = reduce_noise(gray)
    binary = threshold_image(denoised)

    # ছবির total area এর 0.02% এর চেয়ে ছোট shape বাদ দেওয়া হবে (stray fragment)
    min_area = (width * height) * 0.0002

    paths = build_shape_paths(binary, min_area=min_area)

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

def vectorize_image_color(input_path: str, output_svg_path: str, num_colors: int = 8) -> dict:
    """
    Color (রঙিন) মোডে ভেক্টরাইজ করা।

    ধাপ:
        ১. ছবি লোড করা
        ২. quantize_colors দিয়ে রঙগুলোকে num_colors সংখ্যক মূল রঙে ভাগ করা
        ৩. প্রতিটা রঙের জন্য আলাদা binary mask বানানো
           (সেই রঙের পিক্সেল = সাদা/255, বাকি সব = কালো/0)
        ৪. সেই mask থেকে build_shape_paths দিয়ে shape বের করা
        ৫. প্রতিটা shape কে তার নিজস্ব রঙ দিয়ে SVG তে যোগ করা,
           **বড় (ব্যাকগ্রাউন্ড) রঙ আগে, ছোট (ডিটেইল) রঙ সবার শেষে/উপরে**
           - এটা না করলে বড় রঙ পরে আঁকা হয়ে ছোট ডিটেইল ঢেকে ফেলতে পারে
    """
    image = load_image(input_path)
    height, width = image.shape[:2]

    labels_2d, centers = quantize_colors(image, num_colors=num_colors)

    # খুব ছোট shape (নয়েজ) বাদ দেওয়ার জন্য - ছবির total area এর 0.05% এর
    # চেয়ে ছোট shape গুলো বাদ যাবে
    min_area = (width * height) * 0.0005

    dwg = svgwrite.Drawing(output_svg_path, size=(width, height))
    total_shapes = 0
    colors_used = 0

    # ---- গুরুত্বপূর্ণ ফিক্স ----
    # প্রতিটা ক্লাস্টার কত পিক্সেল দখল করে আছে সেটা আগে গুনে নিচ্ছি,
    # তারপর সবচেয়ে বড় (সাধারণত ব্যাকগ্রাউন্ড) থেকে সবচেয়ে ছোট
    # (সাধারণত সূক্ষ্ম ডিটেইল) - এই ক্রমে সাজাচ্ছি। বড় রঙ আগে আঁকলে
    # পরে ছোট/ডিটেইল রঙ তার উপরে বসবে, ফলে সেগুলো ঢাকা পড়বে না।
    cluster_sizes = []
    for cluster_index in range(num_colors):
        pixel_count = int(np.sum(labels_2d == cluster_index))
        cluster_sizes.append((cluster_index, pixel_count))

    cluster_sizes.sort(key=lambda item: item[1], reverse=True)
    ordered_cluster_indices = [idx for idx, _count in cluster_sizes]

    # প্রতিটা ক্লাস্টার/রঙের জন্য - এখন বড় থেকে ছোট ক্রমে - shape বের করা
    # ---- আরেকটা ফিক্স: দুই রঙের সীমান্তে সরু সাদা "ফাঁক" (seam) বন্ধ করা ----
    # সীমান্তের কিছু পিক্সেল (anti-aliasing এর কারণে) কোনো একটা রঙে সঠিকভাবে
    # যায় না, ফলে shape এর মাঝে ছোট ছোট ফাঁক দেখা যায়। প্রতিটা mask কে
    # সামান্য "dilate" (ফুলিয়ে) নিলে shape গুলো একে অপরকে সামান্য ওভারল্যাপ
    # করে, তাই সেই ফাঁক আর চোখে পড়ে না।
    dilate_kernel = np.ones((3, 3), np.uint8)

    for cluster_index in ordered_cluster_indices:
        # এই ক্লাস্টারের রঙ কোথায় কোথায় আছে, তার একটা mask বানানো
        mask = np.uint8(labels_2d == cluster_index) * 255

        # এই রঙ ছবিতে না থাকলে (mask সম্পূর্ণ কালো), স্কিপ করো
        if not np.any(mask):
            continue

        # সামান্য dilate করে সীমান্তের ফাঁক বন্ধ করা (১ পিক্সেল মোটা করা)
        mask = cv2.dilate(mask, dilate_kernel, iterations=1)

        paths = build_shape_paths(mask, min_area=min_area)
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

def vectorize_image(input_path: str, output_svg_path: str, mode: str = "bw", num_colors: int = 8) -> dict:
    """
    এটাই মূল function যেটা API থেকে কল করা হয়। mode অনুযায়ী সঠিক
    পাইপলাইন (bw বা color) চালানো হবে।
    """
    if mode == "color":
        return vectorize_image_color(input_path, output_svg_path, num_colors=num_colors)
    return vectorize_image_bw(input_path, output_svg_path)


# ============================================================
# Step 11: DXF export এর জন্য - shape গুলোকে polygon (পয়েন্টের
# লিস্ট) আকারে বের করা
# ============================================================

def extract_polygons_for_dxf(input_path: str):
    """
    DXF ফরম্যাট (CNC/CAD সফটওয়্যারে ব্যবহার হয়) SVG এর মতো Bezier
    curve সরাসরি সাপোর্ট করে না, এটা মূলত সরলরেখা/polygon দিয়ে কাজ করে।
    তাই DXF এর জন্য আমরা SVG থেকে না গিয়ে, সরাসরি ছবি থেকে প্রতিটা
    shape এর "সরল করা" (simplified) কোণার পয়েন্টগুলো বের করছি।

    RETR_LIST ব্যবহার করছি (RETR_CCOMP এর বদলে) - কারণ DXF তে বাইরের
    shape আর ভিতরের "গর্ত" (hole) কে আলাদা আলাদা বন্ধ (closed) polygon
    হিসেবে রাখলেই CNC/লেজার-কাটিং সফটওয়্যার এমনিতেই বুঝে নেয় কোনটা
    কাটতে হবে কোনটা বাদ দিতে হবে - তাই hierarchy লজিক লাগে না এখানে।

    Returns: (polygons, width, height) - যেখানে polygons হলো
    [[(x1,y1), (x2,y2), ...], [(x1,y1), ...], ...] ধরনের একটা লিস্ট,
    প্রতিটা ভিতরের লিস্ট একটা বন্ধ shape এর কোণার পয়েন্ট।
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
