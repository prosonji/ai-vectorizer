"""
DXF Export (Step 11)

DXF হলো CAD/CNC/লেজার-কাটিং সফটওয়্যারে ব্যবহৃত একটা vector ফরম্যাট
(AutoCAD, LaserCut, ইত্যাদি এটা পড়তে পারে)। SVG এর মতো Bezier curve
DXF সরাসরি সহজে সাপোর্ট করে না - এটা মূলত সরলরেখা/polygon (LWPOLYLINE)
দিয়ে কাজ করে।

ezdxf লাইব্রেরি দিয়ে আমরা প্রতিটা shape এর কোণার পয়েন্টগুলো নিয়ে
একটা করে বন্ধ (closed) polyline বানাচ্ছি।
"""

import ezdxf


def polygons_to_dxf(polygons: list, output_path: str) -> None:
    """
    polygons: [[(x1,y1), (x2,y2), ...], [(x1,y1), ...], ...] -
    প্রতিটা ভিতরের লিস্ট একটা shape এর কোণার পয়েন্ট।

    প্রতিটা polygon কে DXF এ একটা "LWPOLYLINE" (লাইটওয়েট পলিলাইন)
    entity হিসেবে যোগ করা হয়, close=True দিয়ে যাতে shape টা
    স্বয়ংক্রিয়ভাবে বন্ধ (শুরুর পয়েন্টে ফিরে) থাকে।

    DXF এ Y-অক্ষ সাধারণত উপরের দিকে বাড়ে (ছবির/SVG এর উল্টো, যেখানে
    Y নিচের দিকে বাড়ে) - তাই DXF সফটওয়্যারে ছবিটা সোজাভাবে দেখানোর
    জন্য প্রতিটা Y পয়েন্টকে উল্টে (flip) দিচ্ছি।
    """
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # সব shape এর সর্বোচ্চ Y মান বের করছি, Y-flip করার সময় এটা দরকার
    max_y = 0.0
    for points in polygons:
        for _x, y in points:
            if y > max_y:
                max_y = y

    for points in polygons:
        if len(points) < 3:
            continue
        flipped_points = [(x, max_y - y) for x, y in points]
        msp.add_lwpolyline(flipped_points, close=True)

    doc.saveas(output_path)
