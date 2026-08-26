"""
Format Converters (Step 11)

আমাদের কাছে ইতিমধ্যে SVG ফাইল আছে (vectorize করার পর outputs/ ফোল্ডারে
সেভ থাকে)। এই ফাইলে সেই SVG কে PDF আর EPS ফরম্যাটে রূপান্তর করার
ফাংশন আছে।

আমরা "svglib" আর "reportlab" ব্যবহার করছি (Cairo/Inkscape এর মতো
সিস্টেম প্রোগ্রাম না) - কারণ এগুলো pure Python প্যাকেজ, Windows-এ
`pip install` করলেই কাজ করে, আলাদা করে কোনো external প্রোগ্রাম
ইনস্টল করা লাগে না।

কীভাবে কাজ করে:
    ১. svglib দিয়ে SVG ফাইল পড়ে একটা "Drawing" object বানানো
       (এটা reportlab এর নিজস্ব গঠন, যেটা দিয়ে বিভিন্ন ফরম্যাটে
       এক্সপোর্ট করা যায়)
    ২. reportlab এর renderPDF / renderPS মডিউল দিয়ে সেই Drawing
       object কে PDF বা EPS ফাইলে সেভ করা
"""

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPS


def svg_to_pdf(svg_path: str, output_pdf_path: str) -> None:
    """
    একটা SVG ফাইলকে PDF ফাইলে রূপান্তর করা।
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        raise ValueError("SVG ফাইলটা পড়া যায়নি, PDF বানানো সম্ভব হলো না")
    renderPDF.drawToFile(drawing, output_pdf_path)


def svg_to_eps(svg_path: str, output_eps_path: str) -> None:
    """
    একটা SVG ফাইলকে EPS (Encapsulated PostScript) ফাইলে রূপান্তর করা।
    EPS মূলত প্রিন্ট/পুরনো ডিজাইন সফটওয়্যারে ব্যবহারের জন্য জনপ্রিয়
    একটা ভেক্টর ফরম্যাট।
    """
    drawing = svg2rlg(svg_path)
    if drawing is None:
        raise ValueError("SVG ফাইলটা পড়া যায়নি, EPS বানানো সম্ভব হলো না")
    renderPS.drawToFile(drawing, output_eps_path)
